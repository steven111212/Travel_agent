import requests
from datetime import datetime, timedelta
from functools import lru_cache
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WEATHER_API_KEY
from typing import Dict, List, Any, Optional, Union
import re
from collections import Counter

class WeatherService:
    """Weather API Service for Central Weather Bureau (CWA) Taiwan"""
    
    def __init__(self):
        self.api_key = WEATHER_API_KEY
        self.base_url = "https://opendata.cwa.gov.tw/api"
        
    @lru_cache(maxsize=128)
    def get_weather_forecast(self, city: str, location: Optional[str] = None, week: bool = False) -> Optional[Dict[str, Any]]:
        """Get weather forecast data from CWA API."""
        # Set the appropriate city code based on the request type
        if week:
            city_code = {'宜蘭縣':"003", '桃園市':'007', '新竹縣':'011', '苗栗縣':'015', '彰化縣':'019', '南投縣':'023', 
                '雲林縣':'027', '嘉義縣':'031', '屏東縣':'035', '臺東縣':'039','台東縣':'039', '花蓮縣':'043', '澎湖縣':'047', 
                '基隆市':'051', '新竹市':'055', '嘉義市':'059', '臺北市':'063','台北市':'063', '高雄市':'067', '新北市':'071', 
                '臺中市':'075','台中市':'075', '臺南市':'079','台南市':'079', '連江縣':'083', '金門縣':'087'}
        else:
            city_code = {'宜蘭縣':"001", '桃園市':'005', '新竹縣':'009', '苗栗縣':'013', '彰化縣':'017', '南投縣':'021', 
                    '雲林縣':'025', '嘉義縣':'029', '屏東縣':'033', '臺東縣':'037','台東縣':'037', '花蓮縣':'041', '澎湖縣':'045', 
                    '基隆市':'049', '新竹市':'053', '嘉義市':'057', '臺北市':'061','台北市':'061', '高雄市':'065', '新北市':'069', 
                    '臺中市':'073','台中市':'073', '臺南市':'077','台南市':'077', '連江縣':'081', '金門縣':'085'}
        
        if location:
            # API endpoint path
            endpoint = f"/v1/rest/datastore/F-D0047-{city_code[city]}"  # General weather forecast - 36 hour forecast
        elif week:
            endpoint = "/v1/rest/datastore/F-D0047-091"  # Weekly forecast
        else:
            endpoint = "/v1/rest/datastore/F-D0047-089"  # City level forecast
        
        # Request parameters
        params = {
            "Authorization": self.api_key
        }
        
        try:
            # Send GET request
            response = requests.get(self.base_url + endpoint, params=params)
            
            # Check if request was successful
            if response.status_code == 200:
                # Parse JSON response
                return response.json()
            else:
                print(f"API request failed: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"API connection error: {str(e)}")
            return None
            
    def get_multi_day_forecast(self, city: str, location: str, start_date: str, end_date: str) -> Union[str, List[Dict[str, Any]]]:
        """Get weather forecast for a specified date range."""
        # Use weekly forecast API to get data
        weather_data = self.get_weather_forecast(city, location, week=True)
        if not weather_data:
            return "Unable to retrieve multi-day weather data"
        
        # Find the corresponding district
        district_index = -1
        for i, loc in enumerate(weather_data['records']['Locations'][0]['Location']):
            if loc['LocationName'] == location or loc['LocationName'] == city:
                district_index = i
                break
        
        if district_index == -1:
            return "Cannot find specified district in multi-day forecast"
        
        # Convert start_date and end_date to datetime objects
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
        
        # Get current date
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Calculate maximum forecast date (current date + 6 days, total 7 days)
        max_forecast_date = current_date + timedelta(days=6)
        
        # Check if the requested date range exceeds available forecast range
        if start_datetime > max_forecast_date:
            return f"Cannot provide forecast for start date {start_date}, API only provides forecast until {max_forecast_date.strftime('%Y-%m-%d')}"
        
        if end_datetime > max_forecast_date:
            end_datetime = max_forecast_date
        
        # Parse weather data for the date range
        forecast_data = []
        location_data = weather_data['records']['Locations'][0]['Location'][district_index]
        
        # Get various weather elements
        weather_elements = location_data['WeatherElement']
        
        # Create a mapping table to map element codes to names
        element_map = {}
        for element in weather_elements:
            element_map[element['ElementName']] = element['Time']
        
        # Process each day
        current_date = start_datetime
        while current_date <= end_datetime:
            date_str = current_date.strftime("%Y-%m-%d")
            day_data = {"日期": date_str}
            
            # Process each weather element
            for element_name, time_data in element_map.items():
                # Find data for the corresponding date
                day_element_data = []
                for time_point in time_data:
                    start_time = datetime.strptime(time_point['StartTime'], "%Y-%m-%dT%H:%M:%S+08:00")
                    end_time = datetime.strptime(time_point['EndTime'], "%Y-%m-%dT%H:%M:%S+08:00")
                    
                    # Check if the time interval intersects with the current date
                    if (start_time.date() <= current_date.date() <= end_time.date()):
                        day_element_data.append(time_point)
                
                # If found data for this date
                if day_element_data:
                    # Process data based on element type
                    if element_name == '天氣現象':
                        # Only get daytime weather phenomena (6:00-18:00)
                        daytime_data = [d for d in day_element_data if 
                                        '06:00:00' in d['StartTime'] or '12:00:00' in d['StartTime']]
                        if daytime_data:
                            day_data['天氣現象'] = daytime_data[0]['ElementValue'][0]['Weather']
                            day_data['天氣代碼'] = daytime_data[0]['ElementValue'][0]['WeatherCode']
                    
                    elif element_name == '最高溫度':
                        temps = [int(d['ElementValue'][0]['MaxTemperature']) for d in day_element_data]
                        if temps:
                            day_data['最高溫度'] = int(max(temps))
                    
                    elif element_name == '最低溫度':
                        temps = [int(d['ElementValue'][0]['MinTemperature']) for d in day_element_data]
                        if temps:
                            day_data['最低溫度'] = int(min(temps))
                    
                    elif element_name == '平均溫度':
                        temps = [int(d['ElementValue'][0]['Temperature']) for d in day_element_data]
                        if temps:
                            day_data['平均溫度'] = int(sum(temps) / len(temps))
                    
                    elif element_name == '平均相對濕度':
                        humidities = [int(d['ElementValue'][0]['RelativeHumidity']) for d in day_element_data]
                        if humidities:
                            day_data['相對濕度'] = int(sum(humidities) / len(humidities))
                    
                    elif element_name == '風速':
                        speeds = [int(d['ElementValue'][0]['WindSpeed']) for d in day_element_data]
                        if speeds:
                            day_data['風速'] = int(sum(speeds) / len(speeds))
                    
                    elif element_name == '風向':
                        # Get daytime wind direction
                        daytime_data = [d for d in day_element_data if 
                                        '06:00:00' in d['StartTime'] or '12:00:00' in d['StartTime']]
                        if daytime_data:
                            day_data['風向'] = daytime_data[0]['ElementValue'][0]['WindDirection']
                    
                    elif element_name == '12小時降雨機率':
                        # Filter valid precipitation probability data
                        valid_probs = [int(d['ElementValue'][0]['ProbabilityOfPrecipitation']) 
                                        for d in day_element_data 
                                        if d['ElementValue'][0]['ProbabilityOfPrecipitation'] != '-']
                        if valid_probs:
                            day_data['降雨機率'] = max(valid_probs)  # Take maximum precipitation probability
                        else:
                            day_data['降雨機率'] = '-'  # Default to '-' if no valid data
                    
                    elif element_name == '紫外線指數':
                        # Filter daytime UV data
                        day_uv = [d for d in day_element_data if 
                                    '06:00:00' in d['StartTime']]
                        if day_uv:
                            day_data['紫外線指數'] = int(day_uv[0]['ElementValue'][0]['UVIndex'])
                            day_data['紫外線等級'] = day_uv[0]['ElementValue'][0]['UVExposureLevel']
                    
                    elif element_name == '最大舒適度指數':
                        # Get comfort description
                        comfort_data = [d['ElementValue'][0]['MaxComfortIndexDescription'] for d in day_element_data]
                        if comfort_data:
                            # Use the most frequent comfort description
                            day_data['舒適度'] = Counter(comfort_data).most_common(1)[0][0]
                    
                    elif element_name == '天氣預報綜合描述':
                        # Get daytime comprehensive description
                        day_desc = [d for d in day_element_data if 
                                    '06:00:00' in d['StartTime'] or '12:00:00' in d['StartTime']]
                        if day_desc:
                            day_data['天氣綜合描述'] = day_desc[0]['ElementValue'][0]['WeatherDescription']
            
            # Ensure basic data exists
            if '最高溫度' in day_data and '最低溫度' in day_data:
                # If no average temperature, calculate one
                if '平均溫度' not in day_data:
                    day_data['平均溫度'] = int((day_data['最高溫度'] + day_data['最低溫度']) / 2)
                
                # Set default values
                for field in ['降雨機率', '風速', '相對濕度']:
                    if field not in day_data:
                        day_data[field] = 0
                
                if '天氣現象' not in day_data:
                    day_data['天氣現象'] = '晴時多雲'  # Default value
                
                # Add processed data for the day to the result list
                forecast_data.append(day_data)
            
            # Move to the next day
            current_date += timedelta(days=1)
        
        # If no data found, return error message
        if not forecast_data:
            return "Unable to get weather forecast data for the specified date range"
        
        return forecast_data
    
    def get_sunrise_data(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get sunrise and sunset data from CWA API."""
        # API endpoint path
        endpoint = "/v1/rest/datastore/A-B0062-001"
        
        # Request parameters
        params = {
            "Authorization": self.api_key
        }
        
        try:
            # Send GET request
            response = requests.get(self.base_url + endpoint, params=params)
            # Check if request was successful
            if response.status_code == 200:
                # Parse JSON response
                sunrise_data = response.json()
            else:
                print(f"Request failed: {response.status_code}")
                return None
            
            for idx, location in enumerate(sunrise_data['records']['locations']['location']):
                if location['CountyName'] == result['台灣縣市']:
                    break
            sunrise_data = sunrise_data['records']['locations']['location'][idx]['time']
            for data in sunrise_data:
                if data['Date'] == result['日期']:
                    return data
        except Exception as e:
            print(f"Error occurred: {str(e)}")
            return None
            
class WeatherAnalysisService:
    """Weather analysis service"""
    
    def evaluate_outdoor_suitability(self, forecast_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Evaluate which days are suitable for outdoor activities"""
        for day_data in forecast_data:
            score = 100  # Perfect score 100
            
            # Deduct points based on precipitation probability
            if not isinstance(day_data['降雨機率'], str):
                if day_data['降雨機率'] > 70:
                    score -= 60
                elif day_data['降雨機率'] > 30:
                    score -= 30
            
            # Deduct points based on temperature suitability
            temp = day_data['平均溫度']
            if temp < 15 or temp > 30:
                score -= 20
            
            # Deduct points based on wind speed
            if day_data['風速'] > 6:  # Assuming wind speed unit is m/s
                score -= 15
            
            # Deduct points based on weather description
            weather_desc = day_data['天氣現象']
            if any(bad_weather in weather_desc for bad_weather in ["雷", "暴雨", "豪雨", "颱風"]):
                score -= 50
            
            day_data["適宜度分數"] = score
            day_data["適宜度評價"] = "非常適合" if score > 80 else "適合" if score > 60 else "尚可" if score > 40 else "不建議"
        
        return forecast_data
    
    def check_weather_warnings(self, data: List[str]) -> tuple:
        """Check for weather warnings in the data"""
        warnings = []
        rain_prob = 0
        
        # Check each weather description item
        for item in data:
            # Check for thunderstorms
            if '雷' in item:
                warnings.append("⚡ 注意: 有雷雨可能，請避免在戶外開闊地區活動")
            
            # Check wind speed
            if '風速' in item:
                # Parse wind speed
                wind_match = re.search(r'風速.*?(\d+)級', item)
                if wind_match:
                    wind_level = int(wind_match.group(1))
                    if wind_level >= 5:
                        warnings.append("💨 注意: 風速達5級以上，外出時請留意，應避免海邊、登山活動")
            
            # Check temperature
            if '溫度' in item or '攝氏' in item:
                # Parse maximum temperature
                temp_match = re.search(r'溫度攝氏(\d+)至(\d+)度', item)
                if temp_match:
                    min_temp = int(temp_match.group(1))
                    max_temp = int(temp_match.group(2))
                    if max_temp >= 30:
                        warnings.append("☀️ 注意: 天氣炎熱，需適時補充水分避免中暑，請做好防曬措施")
            
            # Check precipitation probability
            if '降雨機率' in item:
                # Parse precipitation probability
                rain_match = re.search(r'降雨機率(\d+)%', item)
                if rain_match:
                    rain_prob = int(rain_match.group(1))
                    if rain_prob >= 70:
                        warnings.append(f"☔ 注意 降雨機率達{rain_prob}% (很可能下雨，請攜帶雨具)")
                    elif 30 <= rain_prob < 70:
                        warnings.append(f"☂️ 注意 降雨機率達{rain_prob}%(可能會下雨，建議準備雨具)")
        
        return warnings, rain_prob