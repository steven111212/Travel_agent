import requests
import json
import os
from fuzzywuzzy import process
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GOOGLE_MAPS_API_KEY, LOCATIONS_JSON_PATH
from typing import Optional, Tuple, Dict, Any
from functools import lru_cache

class LocationService:
    """Google Maps API wrapper for location services"""
    
    def __init__(self):
        self.api_key = GOOGLE_MAPS_API_KEY
        self.json_path = LOCATIONS_JSON_PATH
        self.load_data()
    
    def load_data(self):
        """Load JSON database. Create it if it doesn't exist."""
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        
        if os.path.exists(self.json_path):
            with open(self.json_path, "r", encoding="utf-8") as f:
                try:
                    self.data = json.load(f)
                except json.JSONDecodeError:
                    self.data = {}  # Initialize as empty dict if JSON format error
        else:
            self.data = {}
            self.save_data()

    def save_data(self):
        """Save data back to JSON file"""
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
    
    def get_place_info(self, place_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Get the city and district of a place, first query from JSON file,
        if not found, request from Google Maps API"""
        # First query from JSON file
        if place_name in self.data:
            print(f"Retrieved data from JSON: {self.data[place_name]}")
            return self.data[place_name]['city'], self.data[place_name]['district']
        
        # Try fuzzy matching
        close_match = self.fuzzy_search(place_name)
        if close_match:
            print(f"Fuzzy matching found similar place: {close_match}")
            return self.data[close_match]['city'], self.data[close_match]['district']

        # Special handling for Taipei City
        Taipei_list = ['台北', '台北市', '臺北', '臺北市']
        if place_name in Taipei_list:
            self.data[place_name] = {'city': '臺北市', 'district': None}
            self.save_data()
            return '臺北市', None

        # Call Google API
        city, district = self.call_google_maps_api(place_name)

        # Save to JSON file
        if city:
            self.data[place_name] = {'city': city, 'district': district}
            self.save_data()

        return city, district
    
    def fuzzy_search(self, place_name: str, threshold: int = 80) -> Optional[str]:
        """Use fuzzywuzzy for fuzzy matching, returns the most similar place name"""
        place_list = list(self.data.keys())
        if not place_list:
            return None

        best_match, score = process.extractOne(place_name, place_list)
        if score >= threshold:
            return best_match
        return None
    
    @lru_cache(maxsize=128)
    def call_google_maps_api(self, place_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Call Google Maps API and parse results"""
        base_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            "input": place_name,
            "inputtype": "textquery",
            "fields": "formatted_address",
            "language": "zh-TW",
            "key": self.api_key
        }
        
        response = requests.get(base_url, params=params)
        results = response.json()

        # Ensure there are results
        if "candidates" not in results or not results["candidates"]:
            print(f"Google API couldn't find {place_name}")
            return None, None

        result = results["candidates"][0]["formatted_address"]

        # Define list of Taiwanese cities
        city_list = [
            '台北市', '新北市', '基隆市', '桃園市', '新竹市', '新竹縣',
            '苗栗縣', '台中市', '彰化縣', '南投縣', '雲林縣', '嘉義市',
            '嘉義縣', '台南市', '高雄市', '屏東縣', '宜蘭縣', '花蓮縣',
            '台東縣', '澎湖縣', '金門縣', '連江縣',
            '臺北市', '臺中市', '臺南市', '臺東縣'
        ]

        # Extract city
        city = None
        for c in city_list:
            if c in result:
                city = c
                break
        
        if not city:
            return None, None

        # Extract district/township/city
        city_index = result.index(city)
        city_after = result[city_index + len(city):]

        location_types = ['區', '鄉', '鎮', '市']
        district = None
        for loc in location_types:
            location_index = city_after.find(loc)
            if location_index > 0:
                district = city_after[:location_index + 1]
                break

        return city, district