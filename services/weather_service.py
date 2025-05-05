import requests
from datetime import datetime, timedelta
from functools import lru_cache
import sys
import os
import json
import random
import time
from collections import Counter
import re
from typing import Dict, List, Any, Optional, Union

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WEATHER_API_KEY

class WeatherService:
    """Weather API Service for Central Weather Bureau (CWA) Taiwan with caching support"""
    
    def __init__(self):
        self.api_key = WEATHER_API_KEY
        self.base_url = "https://opendata.cwa.gov.tw/api"
        self.cache_data = {}
        self.last_refresh_time = None
        self.cache_duration = 3600  # 緩存持續時間，單位為秒（1小時）
        self.max_retries = 3       # 最大重試次數
        self.cache_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                          "../data/weather_data_cache.json")
        
        # 嘗試從緩存加載數據
        self._load_cache()
    
    def _load_cache(self) -> bool:
        """
        從緩存文件加載數據
        
        返回:
            bool: 是否成功加載緩存
        """
        try:
            if os.path.exists(self.cache_file_path):
                with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 檢查緩存是否過期
                cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01T00:00:00'))
                if datetime.now() - cache_time < timedelta(seconds=self.cache_duration):
                    # 加載數據
                    self.cache_data = cache_data
                    self.last_refresh_time = cache_time
                    print(f"成功從緩存加載天氣數據，緩存時間: {cache_time.isoformat()}")
                    return True
                else:
                    print("天氣緩存已過期，將在需要時獲取新數據")
            else:
                print("無天氣可用緩存，將在需要時獲取新數據")
            return False
        except Exception as e:
            print(f"讀取天氣緩存時出錯: {str(e)}")
            return False
    
    def _save_cache(self) -> None:
        """將數據保存到緩存文件"""
        try:
            # 添加時間戳
            self.cache_data['timestamp'] = datetime.now().isoformat()
            
            # 確保目錄存在
            os.makedirs(os.path.dirname(self.cache_file_path), exist_ok=True)
            
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
            
            self.last_refresh_time = datetime.now()
            print(f"天氣數據已保存到緩存，時間: {self.last_refresh_time.isoformat()}")
        except Exception as e:
            print(f"保存天氣緩存時出錯: {str(e)}")
    
    def _make_api_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        發送API請求，帶有重試機制
        
        參數:
            endpoint (str): API 端點
            params (Dict, optional): 請求參數
            
        返回:
            Dict: API響應或None（如果請求失敗）
        """
        if params is None:
            params = {}
        
        # 添加 API key
        params["Authorization"] = self.api_key
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(self.base_url + endpoint, params=params)
                response.raise_for_status()  # 檢查HTTP錯誤
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    # 如果是速率限制錯誤且不是最後一次嘗試，等待一段時間後重試
                    wait_time = (2 ** attempt) + random.uniform(0, 1)  # 指數退避策略
                    print(f"天氣API請求被限流，等待 {wait_time:.2f} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    print(f"天氣API請求時出錯: {str(e)}")
                    return None
            except Exception as e:
                print(f"天氣API請求時出錯: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = (2 ** attempt) + random.uniform(0, 1)
                    print(f"等待 {wait_time:.2f} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    return None
    
    def get_weather_forecast(self, city: str, location: Optional[str] = None, week: bool = False) -> Optional[Dict[str, Any]]:
        """
        獲取天氣預報數據，首先嘗試從緩存獲取
        
        參數:
            city (str): 城市名稱
            location (str, optional): 地區名稱
            week (bool): 是否獲取週預報
        
        返回:
            Dict[str, Any]: 天氣預報數據
        """
        # 確定緩存鍵名
        cache_key = f"forecast_{city}_{location}_{week}"
        
        # 嘗試從緩存獲取
        if cache_key in self.cache_data and self.last_refresh_time and \
           (datetime.now() - self.last_refresh_time < timedelta(seconds=self.cache_duration)):
            print(f"從緩存獲取天氣預報: {cache_key}")
            return self.cache_data[cache_key]
        
        # 設置API端點
        if week:
            city_code = {'宜蘭縣':"003", '桃園市':'007', '新竹縣':'011', '苗栗縣':'015', '彰化縣':'019', '南投縣':'023', 
                '雲林縣':'027', '嘉義縣':'031', '屏東縣':'035', '臺東縣':'039','台東縣':'039', '花蓮縣':'043', '澎湖縣':'047', 
                '基隆市':'051', '新竹市':'055', '嘉義市':'059', '臺北市':'063','台北市':'063', '高雄市':'067', '新北市':'071', 
                '臺中市':'075','台中市':'075', '臺南市':'079','台南市':'079', '連江縣':'083', '金門縣':'087'}
            endpoint = "/v1/rest/datastore/F-D0047-091"  # Weekly forecast
        elif location:
            city_code = {'宜蘭縣':"001", '桃園市':'005', '新竹縣':'009', '苗栗縣':'013', '彰化縣':'017', '南投縣':'021', 
                    '雲林縣':'025', '嘉義縣':'029', '屏東縣':'033', '臺東縣':'037','台東縣':'037', '花蓮縣':'041', '澎湖縣':'045', 
                    '基隆市':'049', '新竹市':'053', '嘉義市':'057', '臺北市':'061','台北市':'061', '高雄市':'065', '新北市':'069', 
                    '臺中市':'073','台中市':'073', '臺南市':'077','台南市':'077', '連江縣':'081', '金門縣':'085'}
            endpoint = f"/v1/rest/datastore/F-D0047-{city_code[city]}"  # General weather forecast - 36 hour forecast
        else:
            endpoint = "/v1/rest/datastore/F-D0047-089"  # City level forecast
        
        # 發送API請求
        result = self._make_api_request(endpoint)
        
        if result:
            # 保存到緩存
            self.cache_data[cache_key] = result
            self._save_cache()
            
        return result
    
    def get_multi_day_forecast(self, city: str, location: str, start_date: str, end_date: str) -> Union[str, List[Dict[str, Any]]]:
        """
        獲取多天預報數據，首先嘗試從緩存獲取
        
        參數:
            city (str): 城市名稱
            location (str): 地區名稱
            start_date (str): 開始日期，格式為 YYYY-MM-DD
            end_date (str): 結束日期，格式為 YYYY-MM-DD
        
        返回:
            Union[str, List[Dict[str, Any]]]: 多天預報數據或錯誤消息
        """
        # 確定緩存鍵名
        cache_key = f"multi_day_{city}_{location}_{start_date}_{end_date}"
        
        # 嘗試從緩存獲取
        if cache_key in self.cache_data and self.last_refresh_time and \
           (datetime.now() - self.last_refresh_time < timedelta(seconds=self.cache_duration)):
            print(f"從緩存獲取多天預報: {cache_key}")
            return self.cache_data[cache_key]
        
        # 使用週預報API獲取數據
        weather_data = self.get_weather_forecast(city, location, week=True)
        if not weather_data:
            return "Unable to retrieve multi-day weather data"
        
        # 找到對應的地區
        district_index = -1
        for i, loc in enumerate(weather_data['records']['Locations'][0]['Location']):
            if loc['LocationName'] == location or loc['LocationName'] == city:
                district_index = i
                break
        
        if district_index == -1:
            return "Cannot find specified district in multi-day forecast"
        
        # 轉換起始日期和結束日期為datetime對象
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 獲取當前日期
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 計算最大預報日期（當前日期 + 6天，共7天）
        max_forecast_date = current_date + timedelta(days=6)
        
        # 檢查請求的日期範圍是否超出可用預報範圍
        if start_datetime > max_forecast_date:
            return f"Cannot provide forecast for start date {start_date}, API only provides forecast until {max_forecast_date.strftime('%Y-%m-%d')}"
        
        if end_datetime > max_forecast_date:
            end_datetime = max_forecast_date
        
        # 解析日期範圍的天氣數據
        forecast_data = []
        location_data = weather_data['records']['Locations'][0]['Location'][district_index]
        
        # 獲取各種天氣元素
        weather_elements = location_data['WeatherElement']
        
        # 創建一個映射表將元素代碼映射到名稱
        element_map = {}
        for element in weather_elements:
            element_map[element['ElementName']] = element['Time']
        
        # 處理每一天
        current_date = start_datetime
        while current_date <= end_datetime:
            date_str = current_date.strftime("%Y-%m-%d")
            day_data = {"日期": date_str}
            
            # 處理每個天氣元素
            for element_name, time_data in element_map.items():
                # 查找相應日期的數據
                day_element_data = []
                for time_point in time_data:
                    start_time = datetime.strptime(time_point['StartTime'], "%Y-%m-%dT%H:%M:%S+08:00")
                    end_time = datetime.strptime(time_point['EndTime'], "%Y-%m-%dT%H:%M:%S+08:00")
                    
                    # 檢查時間間隔是否與當前日期相交
                    if (start_time.date() <= current_date.date() <= end_time.date()):
                        day_element_data.append(time_point)
                
                # 如果找到了這個日期的數據
                if day_element_data:
                    # 根據元素類型處理數據
                    if element_name == '天氣現象':
                        # 只獲取白天天氣現象（6:00-18:00）
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
                        # 獲取白天風向
                        daytime_data = [d for d in day_element_data if 
                                        '06:00:00' in d['StartTime'] or '12:00:00' in d['StartTime']]
                        if daytime_data:
                            day_data['風向'] = daytime_data[0]['ElementValue'][0]['WindDirection']
                    
                    elif element_name == '12小時降雨機率':
                        # 過濾有效降水概率數據
                        valid_probs = [int(d['ElementValue'][0]['ProbabilityOfPrecipitation']) 
                                        for d in day_element_data 
                                        if d['ElementValue'][0]['ProbabilityOfPrecipitation'] != '-']
                        if valid_probs:
                            day_data['降雨機率'] = max(valid_probs)  # 取最大降水概率
                        else:
                            day_data['降雨機率'] = '-'  # 如果沒有有效數據，則默認為'-'
                    
                    elif element_name == '紫外線指數':
                        # 過濾白天紫外線數據
                        day_uv = [d for d in day_element_data if 
                                    '06:00:00' in d['StartTime']]
                        if day_uv:
                            day_data['紫外線指數'] = int(day_uv[0]['ElementValue'][0]['UVIndex'])
                            day_data['紫外線等級'] = day_uv[0]['ElementValue'][0]['UVExposureLevel']
                    
                    elif element_name == '最大舒適度指數':
                        # 獲取舒適度描述
                        comfort_data = [d['ElementValue'][0]['MaxComfortIndexDescription'] for d in day_element_data]
                        if comfort_data:
                            # 使用最頻繁的舒適度描述
                            day_data['舒適度'] = Counter(comfort_data).most_common(1)[0][0]
                    
                    elif element_name == '天氣預報綜合描述':
                        # 獲取白天綜合描述
                        day_desc = [d for d in day_element_data if 
                                    '06:00:00' in d['StartTime'] or '12:00:00' in d['StartTime']]
                        if day_desc:
                            day_data['天氣綜合描述'] = day_desc[0]['ElementValue'][0]['WeatherDescription']
            
            # 確保基本數據存在
            if '最高溫度' in day_data and '最低溫度' in day_data:
                # 如果沒有平均溫度，則計算一個
                if '平均溫度' not in day_data:
                    day_data['平均溫度'] = int((day_data['最高溫度'] + day_data['最低溫度']) / 2)
                
                # 設置默認值
                for field in ['降雨機率', '風速', '相對濕度']:
                    if field not in day_data:
                        day_data[field] = 0
                
                if '天氣現象' not in day_data:
                    day_data['天氣現象'] = '晴時多雲'  # 默認值
                
                # 將處理後的當天數據添加到結果列表
                forecast_data.append(day_data)
            
            # 移至下一天
            current_date += timedelta(days=1)
        
        # 如果沒有找到數據，則返回錯誤消息
        if not forecast_data:
            return "Unable to get weather forecast data for the specified date range"
        
        # 存入緩存
        self.cache_data[cache_key] = forecast_data
        self._save_cache()
        
        return forecast_data
    
    def get_sunrise_data(self, location_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        從CWA API獲取日出和日落數據
        
        參數:
            location_info (Dict[str, Any]): 包含縣市和日期的位置信息
            
        返回:
            Optional[Dict[str, Any]]: 日出日落數據或 None（如果請求失敗）
        """
        # 緩存鍵名
        city = location_info.get('台灣縣市', '')
        date = location_info.get('日期', '')
        cache_key = f"sunrise_{city}_{date}"
        
        # 嘗試從緩存獲取
        if cache_key in self.cache_data and self.last_refresh_time and \
           (datetime.now() - self.last_refresh_time < timedelta(seconds=self.cache_duration)):
            print(f"從緩存獲取日出日落信息: {cache_key}")
            return self.cache_data[cache_key]
        
        # API端點路徑
        endpoint = "/v1/rest/datastore/A-B0062-001"
        
        try:
            # 發送GET請求
            sunrise_data = self._make_api_request(endpoint)
            
            if sunrise_data:
                # 解析JSON響應
                for idx, location in enumerate(sunrise_data['records']['locations']['location']):
                    if location['CountyName'] == city:
                        found_data = sunrise_data['records']['locations']['location'][idx]['time']
                        for data in found_data:
                            if data['Date'] == date:
                                # 保存到緩存
                                self.cache_data[cache_key] = data
                                self._save_cache()
                                return data
            
            return None
        except Exception as e:
            print(f"獲取日出日落數據時出錯: {str(e)}")
            return None

class WeatherAnalysisService:
    """Weather analysis service"""
    
    def evaluate_outdoor_suitability(self, forecast_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        評估哪些天適合戶外活動
        
        參數:
            forecast_data (List[Dict[str, Any]]): 多天預報數據
            
        返回:
            List[Dict[str, Any]]: 添加了適宜度評估的預報數據
        """
        for day_data in forecast_data:
            score = 100  # 完美分數100
            
            # 根據降水概率扣分
            if not isinstance(day_data['降雨機率'], str):
                if day_data['降雨機率'] > 70:
                    score -= 60
                elif day_data['降雨機率'] > 30:
                    score -= 30
            
            # 根據溫度適宜性扣分
            temp = day_data['平均溫度']
            if temp < 15 or temp > 30:
                score -= 20
            
            # 根據風速扣分
            if day_data['風速'] > 6:  # 假設風速單位為m/s
                score -= 15
            
            # 根據天氣描述扣分
            weather_desc = day_data['天氣現象']
            if any(bad_weather in weather_desc for bad_weather in ["雷", "暴雨", "豪雨", "颱風"]):
                score -= 50
            
            day_data["適宜度分數"] = score
            day_data["適宜度評價"] = "非常適合" if score > 80 else "適合" if score > 60 else "尚可" if score > 40 else "不建議"
        
        return forecast_data
    
    def check_weather_warnings(self, data: List[str]) -> tuple:
        """
        檢查數據中的天氣警告
        
        參數:
            data (List[str]): 天氣描述列表
            
        返回:
            tuple: (警告列表, 降雨概率)
        """
        warnings = []
        rain_prob = 0
        
        # 檢查每個天氣描述項
        for item in data:
            # 檢查雷暴
            if '雷' in item:
                warnings.append("⚡ 注意: 有雷雨可能，請避免在戶外開闊地區活動")
            
            # 檢查風速
            if '風速' in item:
                # 解析風速
                wind_match = re.search(r'風速.*?(\d+)級', item)
                if wind_match:
                    wind_level = int(wind_match.group(1))
                    if wind_level >= 5:
                        warnings.append("💨 注意: 風速達5級以上，外出時請留意，應避免海邊、登山活動")
            
            # 檢查溫度
            if '溫度' in item or '攝氏' in item:
                # 解析最高溫度
                temp_match = re.search(r'溫度攝氏(\d+)至(\d+)度', item)
                if temp_match:
                    min_temp = int(temp_match.group(1))
                    max_temp = int(temp_match.group(2))
                    if max_temp >= 30:
                        warnings.append("☀️ 注意: 天氣炎熱，需適時補充水分避免中暑，請做好防曬措施")
            
            # 檢查降水概率
            if '降雨機率' in item:
                # 解析降水概率
                rain_match = re.search(r'降雨機率(\d+)%', item)
                if rain_match:
                    rain_prob = int(rain_match.group(1))
                    if rain_prob >= 70:
                        warnings.append(f"☔ 注意 降雨機率達{rain_prob}% (很可能下雨，請攜帶雨具)")
                    elif 30 <= rain_prob < 70:
                        warnings.append(f"☂️ 注意 降雨機率達{rain_prob}%(可能會下雨，建議準備雨具)")
        
        return warnings, rain_prob