import requests
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GOOGLE_MAPS_API_KEY  # 直接導入根目錄的 config.py
from fuzzywuzzy import process

class LocationAPI:
    """Google Maps API 封裝"""
    
    def __init__(self):
        self.api_key = GOOGLE_MAPS_API_KEY
        self.json_path = "locations.json"
        self.load_data()
    
    def load_data(self):
        """載入 JSON 資料庫，如果檔案不存在則建立"""
        if os.path.exists(self.json_path):
            with open(self.json_path, "r", encoding="utf-8") as f:
                try:
                    self.data = json.load(f)
                except json.JSONDecodeError:
                    self.data = {}  # JSON 格式錯誤時，初始化為空字典
        else:
            self.data = {}

    def save_data(self):
        """將資料存回 JSON 檔案"""
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)
    
    def get_place_info(self, place_name):
        """取得地點的縣市與地區，先從 JSON 檔案查詢，查無則請求 Google Maps API"""
        # 先從 JSON 檔案查詢
        if place_name in self.data:
            print(f"從 JSON 取得資料: {self.data[place_name]}")
            return self.data[place_name]['city'], self.data[place_name]['district']
        
        # 嘗試模糊匹配
        close_match = self.fuzzy_search(place_name)
        if close_match:
            print(f"模糊匹配找到相似地點: {close_match}")
            return self.data[close_match]['city'], self.data[close_match]['district']

        # 台北市特殊處理
        Taipei_list = ['台北', '台北市', '臺北', '臺北市']
        if place_name in Taipei_list:
            self.data[place_name] = {'city': '臺北市', 'district': None}
            self.save_data()
            return '臺北市', None

        # 呼叫 Google API
        city, district = self.call_google_maps_api(place_name)

        # 儲存到 JSON 檔案
        if city:
            self.data[place_name] = {'city': city, 'district': district}
            self.save_data()

        return city, district
    
    def fuzzy_search(self, place_name, threshold=80):
        """使用 fuzzywuzzy 進行模糊匹配，返回最相近的地點名稱"""
        place_list = list(self.data.keys())
        if not place_list:
            return None

        best_match, score = process.extractOne(place_name, place_list)
        if score >= threshold:
            return best_match
        return None
    
    
    def call_google_maps_api(self, place_name):
        """呼叫 Google Maps API 並解析結果"""
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

        # 確保有回傳結果
        if "candidates" not in results or not results["candidates"]:
            print(f"Google API 找不到 {place_name}")
            return None, None

        result = results["candidates"][0]["formatted_address"]

        # 定義台灣縣市列表
        city_list = [
            '台北市', '新北市', '基隆市', '桃園市', '新竹市', '新竹縣',
            '苗栗縣', '台中市', '彰化縣', '南投縣', '雲林縣', '嘉義市',
            '嘉義縣', '台南市', '高雄市', '屏東縣', '宜蘭縣', '花蓮縣',
            '台東縣', '澎湖縣', '金門縣', '連江縣',
            '臺北市', '臺中市', '臺南市', '臺東縣'
        ]

        # 提取縣市
        city = None
        for c in city_list:
            if c in result:
                city = c
                break
        
        if not city:
            return None, None

        # 提取區/鄉/鎮/市
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
    
