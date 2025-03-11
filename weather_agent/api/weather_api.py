import requests
from datetime import datetime, timedelta
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import WEATHER_API_KEY
from functools import lru_cache

class WeatherAPI:
    """中央氣象局 API 封裝"""
    
    def __init__(self):
        self.api_key = WEATHER_API_KEY
        self.base_url = "https://opendata.cwa.gov.tw/api"
    
    @lru_cache(maxsize=128)
    def get_weather_forecast(self, city, location, week=False):
        # 設定基本 URL
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
        
        base_url = "https://opendata.cwa.gov.tw/api"
        
        if location:
            # API 端點路徑
            endpoint = "/v1/rest/datastore/F-D0047-"+city_code[city]  # 一般天氣預報-今明 36 小時天氣預報
        elif week:
            endpoint = "/v1/rest/datastore/F-D0047-091"
        else:
            endpoint = "/v1/rest/datastore/F-D0047-089"

        api_key = self.api_key
        
        # 設定請求參數
        params = {
            "Authorization": api_key
        }
        
        try:
            # 發送 GET 請求
            response = requests.get(base_url + endpoint, params=params)
            
            # 檢查請求是否成功
            if response.status_code == 200:
                # 解析 JSON 回應
                return response.json()
            else:
                print(f"API請求失敗: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"API連線錯誤: {str(e)}")
            return None
    def get_multi_day_forecast(self, city, location, start_date, end_date):
        """獲取指定日期範圍的天氣預報"""
        # 使用週預報API獲取資料
        weather_data = self.get_weather_forecast(city, location, week=True)
        if not weather_data:
            return "無法獲取多日天氣數據"
        
        # 找到對應地區
        district_index = -1
        for i, loc in enumerate(weather_data['records']['Locations'][0]['Location']):
            if loc['LocationName'] == location or loc['LocationName'] == city:
                district_index = i
                break
        
        if district_index == -1:
            return "找不到指定的行政區多日預報"
        
        # 將start_date和end_date轉換為datetime物件
        start_datetime = datetime.strptime(start_date, "%Y-%m-%d")
        end_datetime = datetime.strptime(end_date, "%Y-%m-%d")
        
        # 獲取當前日期
        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 計算API提供的最大預報日期 (當前日期 + 6天，共7天)
        max_forecast_date = current_date + timedelta(days=6)
        
        # 檢查請求的日期範圍是否超出可用預報範圍
        if start_datetime > max_forecast_date:
            return f"無法提供開始日期 {start_date} 的天氣預報，氣象局API僅提供至 {max_forecast_date.strftime('%Y-%m-%d')} 的預報"
        
        
        if end_datetime > max_forecast_date:
            end_datetime = max_forecast_date
        
        # 解析日期範圍內的天氣數據
        forecast_data = []
        location_data = weather_data['records']['Locations'][0]['Location'][district_index]
        
        # 取得各種天氣要素
        weather_elements = location_data['WeatherElement']
        
        # 創建一個映射表，將要素代碼映射到名稱
        element_map = {}
        for element in weather_elements:
            element_map[element['ElementName']] = element['Time']
        
        
        # 對每一天進行處理
        current_date = start_datetime
        while current_date <= end_datetime:
            date_str = current_date.strftime("%Y-%m-%d")
            day_data = {"日期": date_str}
            # 針對每個天氣要素處理
            for element_name, time_data in element_map.items():
                # 查找對應日期的資料
                day_element_data = []
                for time_point in time_data:
                    start_time = datetime.strptime(time_point['StartTime'], "%Y-%m-%dT%H:%M:%S+08:00")
                    end_time = datetime.strptime(time_point['EndTime'], "%Y-%m-%dT%H:%M:%S+08:00")
                    
                    # 檢查時間區間是否與當前日期相交
                    if (start_time.date() <= current_date.date() <= end_time.date()):
                        day_element_data.append(time_point)
                
                # 如果找到了該日期的相關資料
                if day_element_data:
                    # 根據天氣要素類型處理資料
                    if element_name == '天氣現象':
                        # 只取日間的天氣現象(6:00-18:00)
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
                        # 取日間的風向
                        daytime_data = [d for d in day_element_data if 
                                        '06:00:00' in d['StartTime'] or '12:00:00' in d['StartTime']]
                        if daytime_data:
                            day_data['風向'] = daytime_data[0]['ElementValue'][0]['WindDirection']
                    
                    elif element_name == '12小時降雨機率':
                        # 過濾出有效的降雨機率數據
                        valid_probs = [int(d['ElementValue'][0]['ProbabilityOfPrecipitation']) 
                                        for d in day_element_data 
                                        if d['ElementValue'][0]['ProbabilityOfPrecipitation'] != '-']
                        if valid_probs:
                            day_data['降雨機率'] = max(valid_probs)  # 取最大降雨機率
                        else:
                            day_data['降雨機率'] = '-'  # 如果沒有有效資料，預設為'-'
                    
                    elif element_name == '紫外線指數':
                        # 過濾白天的紫外線資料
                        day_uv = [d for d in day_element_data if 
                                    '06:00:00' in d['StartTime']]
                        if day_uv:
                            day_data['紫外線指數'] = int(day_uv[0]['ElementValue'][0]['UVIndex'])
                            day_data['紫外線等級'] = day_uv[0]['ElementValue'][0]['UVExposureLevel']
                    
                    elif element_name == '最大舒適度指數':
                        # 取得舒適度描述
                        comfort_data = [d['ElementValue'][0]['MaxComfortIndexDescription'] for d in day_element_data]
                        if comfort_data:
                            # 使用出現頻率最高的舒適度描述
                            from collections import Counter
                            day_data['舒適度'] = Counter(comfort_data).most_common(1)[0][0]
                    
                    elif element_name == '天氣預報綜合描述':
                        # 取白天的綜合描述
                        day_desc = [d for d in day_element_data if 
                                    '06:00:00' in d['StartTime'] or '12:00:00' in d['StartTime']]
                        if day_desc:
                            day_data['天氣綜合描述'] = day_desc[0]['ElementValue'][0]['WeatherDescription']
            
            # 確保基本資料都存在
            if '最高溫度' in day_data and '最低溫度' in day_data:
                # 如果沒有平均溫度，計算一個
                if '平均溫度' not in day_data:
                    day_data['平均溫度'] = int((day_data['最高溫度'] + day_data['最低溫度']) / 2)
                
                # 設定默認值
                for field in ['降雨機率', '風速', '相對濕度']:
                    if field not in day_data:
                        day_data[field] = 0
                
                if '天氣現象' not in day_data:
                    day_data['天氣現象'] = '晴時多雲'  # 預設值
                
                # 將處理好的當日資料加入到結果列表
                forecast_data.append(day_data)
            
            # 前進到下一天
            current_date += timedelta(days=1)
        
        # 如果沒有找到任何數據，返回錯誤信息
        if not forecast_data:
            return "無法獲取指定日期範圍的天氣預報數據"
        
        return forecast_data
    
    def get_sunrise_data(self, result):

        base_url = "https://opendata.cwa.gov.tw/api"
        
        # API 端點路徑 (從圖片中可以看到的預報API路徑)
        endpoint = "/v1/rest/datastore/A-B0062-001"  # 一般天氣預報-今明 36 小時天氣預報
        
        # 你需要一個 API 授權金鑰
        api_key = self.api_key
        
        # 設定請求參數
        params = {
            "Authorization": api_key
        }
        
        try:
            # 發送 GET 請求
            response = requests.get(base_url + endpoint, params=params)
            # 檢查請求是否成功
            if response.status_code == 200:
                # 解析 JSON 回應
                sunrise_data = response.json()
            else:
                print(f"請求失敗: {response.status_code}")
                return None
            
            for idx, location in enumerate(sunrise_data['records']['locations']['location']):
                if location['CountyName'] == result['台灣縣市']:
                    break
            sunrise_data = sunrise_data['records']['locations']['location'][idx]['time']
            for data in sunrise_data:
                if data['Date'] == result['日期']:
                    return data
        except Exception as e:
            print(f"發生錯誤: {str(e)}")
            return None