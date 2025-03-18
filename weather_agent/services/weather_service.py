import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from api import WeatherAPI, LocationAPI, llmAPI
from utils import check_time_difference, get_default_time, format_time, create_prompt
from .analysis_service import WeatherAnalysisService

logger = logging.getLogger(__name__)

class WeatherService:
    """天氣查詢服務"""
    
    def __init__(self):
        self.weather_api = WeatherAPI()
        self.location_api = LocationAPI()
        self.llm_api = llmAPI()
    
    def query_weather(self, user_query: str) -> Dict[str, Any]:
        """處理用戶的天氣查詢"""
        try:
            # 生成prompt並查詢LLM
            prompt = create_prompt(user_query)
            response_json = self.llm_api.query(prompt)
            result = json.loads(response_json)
            
            # 解析地點信息
            city, location = self.location_api.get_place_info(result['地點'])
            result['台灣縣市'] = city
            result['鄉鎮市區'] = location
            # 處理時間格式
            if result['查詢類型'] == '單日':
                result['時間'] = format_time(result['時間'])
            
            # 取代「台」為「臺」(如有需要)
            if "台" in result.get("台灣縣市", ""):
                result["台灣縣市"] = result["台灣縣市"].replace("台", "臺")
                
            return result
            
        except Exception as e:
            logger.error(f"LLM查詢失敗: {e}")
            raise Exception(f"😢 抱歉，我不太確定您指的是哪個地點。可以請您提供更詳細的名稱嗎？")
    
    def get_single_day_weather(self, query_result: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 獲取天氣描述
            weather_desc = self.find_weather_description(query_result)
            
            # 獲取日出日落資料 - 修改這裡
            sunrise_data = self.weather_api.get_sunrise_data(query_result)
            
            # 組合結果
            return {
                'city': query_result['台灣縣市'],
                'district': query_result['鄉鎮市區'],
                'date': query_result['日期'],
                'time': query_result['時間'],
                'weather_description': weather_desc,
                'sunrise': sunrise_data.get('SunRiseTime', ''),
                'sunset': sunrise_data.get('SunSetTime', ''),
                'notices': weather_desc.split("。")
            }
        except Exception as e:
            logger.error(f"獲取單日天氣資訊失敗: {e}")
            raise
    
    def get_multi_day_weather(self, query_result: Dict[str, Any]) :
        """獲取多日天氣資訊"""
        try:
            # 使用週預報API獲取資料
            forecast_data = self.weather_api.get_multi_day_forecast(
                query_result['台灣縣市'], 
                query_result['鄉鎮市區'], 
                query_result['開始日期'], 
                query_result['結束日期']
            )
            
            # 評估戶外適宜度
            analysis_service = WeatherAnalysisService()
            evaluated_data = analysis_service.evaluate_outdoor_suitability(forecast_data)

            # 轉換為模型對象
            return evaluated_data
        except Exception as e:
            logger.error(f"獲取多日天氣資訊失敗: {e}")
            raise
    
    def find_weather_description(self, LLM_response) -> str:

        try:
            #在天氣資料中找出指定行政區的資料
            week_bool = check_time_difference(LLM_response)  #檢查天數是否超過3天
            weather_data = self.weather_api.get_weather_forecast(LLM_response['台灣縣市'], LLM_response['鄉鎮市區'], week_bool)
            if not weather_data:
                    return "無法獲取天氣數據"
            district_index = -1
            if LLM_response['鄉鎮市區']:
                for i, location in enumerate(weather_data['records']['Locations'][0]['Location']):
                    if location['LocationName'] == LLM_response['鄉鎮市區']:
                        district_index = i
                        break
            else:
                for i, location in enumerate(weather_data['records']['Locations'][0]['Location']):
                    if location['LocationName'] == LLM_response['台灣縣市'] or location['LocationName'] == LLM_response['台灣縣市'].replace("台", "臺"):
                        district_index = i
                        break
                    
            if district_index == -1:
                return "找不到指定的行政區"
            
            time_data = weather_data['records']['Locations'][0]['Location'][district_index]['WeatherElement'][-1]['Time']
            # 將目標時間字串轉換為datetime物件
            target_datetime = datetime.strptime(f"{LLM_response['日期']} {LLM_response['時間']}", "%Y-%m-%d %H:%M")
            # 搜尋符合的時間區間
            for interval in time_data:
                start_time = datetime.strptime(interval['StartTime'], "%Y-%m-%dT%H:%M:%S+08:00")
                end_time = datetime.strptime(interval['EndTime'], "%Y-%m-%dT%H:%M:%S+08:00")
                
                if start_time <= target_datetime <= end_time:
                    return interval['ElementValue'][0]['WeatherDescription']
            first_start_time = datetime.strptime(time_data[0]['StartTime'], "%Y-%m-%dT%H:%M:%S+08:00")
            last_end_time = datetime.strptime(time_data[-1]['EndTime'], "%Y-%m-%dT%H:%M:%S+08:00")
            # 檢查是否在第一筆資料前3小時內
            if first_start_time - timedelta(hours=3) <= target_datetime < first_start_time:
                return time_data[0]['ElementValue'][0]['WeatherDescription']
            
            # 檢查是否在最後一筆資料後3小時內
            if last_end_time < target_datetime <= last_end_time + timedelta(hours=3):
                return time_data[-1]['ElementValue'][0]['WeatherDescription']
            
            return "找不到指定時間的天氣資料"
        except Exception as e:
                logger.error(f"獲取天氣描述時發生錯誤: {e}")
                return f"獲取天氣資料時發生錯誤: {str(e)}"