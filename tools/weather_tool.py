from typing import Dict, List, Any, Optional, Union, Literal, ClassVar, Type
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.location_service import LocationService
from services.scenery_service import SceneryService
from services.weather_service import WeatherService, WeatherAnalysisService
from langchain.tools import BaseTool
import random
from datetime import datetime, timedelta
from config import LLM_BASE_URL, API_TYPE, MODEL, LLM_API_KEY
import litellm
import json
import re

class WeatherTool(BaseTool):
    name: ClassVar[str] = "weather_tool"
    description: ClassVar[str] = "獲取位置的天氣資訊，支援單日或多日查詢"
    
    def __init__(self):
        super().__init__()
        # 初始化所有需要的服務
        self._weather_service = WeatherService()
        self._analysis_service = WeatherAnalysisService()
        self._location_service = LocationService()
        self._scenery_service = SceneryService()
    
    def _run(self, query_input: str, history_messages: list) -> str:
        """所有天氣查詢的統一入口點"""
        try:
            # 步驟1：解析查詢類型和位置
            parsed_response = llm_api(query_input, history_messages)
            
            # 步驟2：使用LocationService解析位置
            location_info = self._resolve_location(parsed_response["地點"])
            if not parsed_response["地點"] or not location_info["台灣縣市"]:
                return f"不好意思，我需要知道您想查詢台灣的哪個縣市或地區才能提供準確的天氣資訊。"
            
            # 字典更新
            parsed_response.update(location_info)

            # 步驟3：根據查詢類型調用相應的處理函數
            if parsed_response["查詢類型"] == "單日":
                return self._handle_single_day_query(parsed_response)
            elif parsed_response["查詢類型"] == "多日":
                return self._handle_multi_day_query(parsed_response)
            else:
                return "抱歉，無法識別查詢類型，請指定是單日或多日查詢"
        
        except Exception as e:
            return f"處理天氣查詢時發生錯誤: {str(e)}"
    
    def _resolve_location(self, place_name: str) -> Dict[str, Optional[str]]:
        """從地點名稱中提取城市和區域"""
        city, district = self._location_service.get_place_info(place_name)
        
        # 替換"台"為"臺"（如需要）
        if city and "台" in city:
            city = city.replace("台", "臺")
            
        return {"台灣縣市": city, "鄉鎮市區": district}
    
    def _handle_single_day_query(self, query_info: Dict[str, Any]) -> str:
        """處理單日天氣查詢"""
        try:
            # 獲取天氣資料
            weather_data = self._get_single_day_weather(query_info)
            
            # 組織回應
            response = self._format_single_day_response(weather_data)
            
            return response
        except Exception as e:
            return f"處理單日天氣查詢時發生錯誤: {str(e)}"
    
    def _handle_multi_day_query(self, query_info: Dict[str, Any]) -> str:
        """處理多日天氣查詢"""
        try:
            city = query_info["台灣縣市"]
            district = query_info["鄉鎮市區"]
            start_date = query_info.get("開始日期")
            end_date = query_info.get("結束日期")

            # 使用緩存版本的 WeatherService 獲取多日天氣預報
            forecast_data = self._weather_service.get_multi_day_forecast(city, district, start_date, end_date)

            if isinstance(forecast_data, str):
                # 錯誤消息
                return f"抱歉，獲取{city}多日天氣資訊時發生錯誤: {forecast_data}"
            
            # 評估戶外適宜度
            forecast_data = self._analysis_service.evaluate_outdoor_suitability(forecast_data)
            
            # 格式化響應
            response = ""
            
            # 添加天氣趨勢圖 (已內建)
            response += display_weather_trend(forecast_data)
            
            # 添加查詢期間信息
            start_date = forecast_data[0]['日期']
            end_date = forecast_data[-1]['日期']
            response += f"\n🗓️ 查詢期間: {start_date} 至 {end_date}"
            location_info = f"\n🌏 地點: {city}"
            if district:
                location_info += f" - {district}"
            response += location_info
            response += "\n-----------------------------------------------------------"
            
            # 輸出每一天的天氣資訊
            for day in forecast_data:
                # 基本天氣資訊
                response += f"\n📅 日期: {day['日期']}"
                response += f"\n🌤 天氣狀況: {day['天氣現象']}"
                response += f"\n🌡️ 溫度區間: {day['最低溫度']}°C - {day['最高溫度']}°C"
                
                # 降雨機率信息
                if not isinstance(day['降雨機率'], str):
                    rain_prob = day['降雨機率']
                    if rain_prob > 70:
                        response += f"\n☔ 降雨機率: {rain_prob}% (很可能下雨，請攜帶雨具)"
                    elif rain_prob > 30:
                        response += f"\n☂️ 降雨機率: {rain_prob}% (可能會下雨，建議準備雨具)"
                    else:
                        response += f"\n☀️ 降雨機率: {rain_prob}% (降雨機率低)"
                
                # 舒適度
                if '舒適度' in day:
                    comfort = day['舒適度'].strip()
                    response += f"\n😌 舒適程度: {comfort}"

                # 溫度提醒 (最低溫度<15°C時才提醒)
                if day['最低溫度'] <= 15:
                    response += f"\n❄️ 注意: 天氣寒冷，請穿著保暖衣物！"
                
                # 溫度提醒 (最高溫度>30°C時才提醒)
                if day['最高溫度'] >= 30:
                    response += f"\n☀️ 注意: 天氣炎熱，需適時補充水分避免中暑，請做好防曬措施"
                
                # 風速提醒 (風速5級以上才提醒)
                if day['風速'] >= 5:
                    response += f"\n💨 注意: {day['風向'].strip()} 風速達{day['風速']}級，外出時請留意，應避免海邊、登山活動"
                
                # 紫外線提醒 (紫外線指數6以上才提醒)
                if '紫外線指數' in day and day['紫外線指數'] >= 6:
                    response += f"\n☀️ 注意: 紫外線指數為{day['紫外線指數']}，請做好防曬措施"
                    
                # 其他特別提醒 (可以根據天氣現象添加)
                if "雷" in day['天氣現象']:
                    response += "\n⚡ 注意: 有雷雨可能，請避免在戶外開闊地區活動"
                
                response += "\n-----------------------------------------------------------"
            
            return response
        
        except Exception as e:
            return f"抱歉，處理多日天氣查詢時發生錯誤: {str(e)}"
    
    def _get_single_day_weather(self, query_info: Dict[str, Any]) -> Dict[str, Any]:
        """獲取單日天氣資料"""
        # 從查詢信息獲取天氣描述
        weather_desc = self._find_weather_description(query_info)
        # 獲取日出日落數據
        sunrise_data = self._weather_service.get_sunrise_data(query_info)

        return {
            'city': query_info['台灣縣市'],
            'district': query_info.get('鄉鎮市區'),
            'date': query_info['日期'],
            'time': query_info['時間'],
            'weather_description': weather_desc,
            'sunrise': sunrise_data.get('SunRiseTime', '') if sunrise_data else '資料不可用',
            'sunset': sunrise_data.get('SunSetTime', '') if sunrise_data else '資料不可用',
            'notices': weather_desc.split("。")
        }
    
    def _format_single_day_response(self, weather_data: Dict[str, Any]) -> str:
        """格式化單日天氣回應"""
        response = ""
        response += f"\n查詢結果:"
        response += f"\n🌏 地點: {weather_data['city']}"
        if weather_data['district']:
            response += f" - {weather_data['district']}"
        response += f"\n📅 時間: {weather_data['date']} {weather_data['time']}"
        response += f"\n🌤 天氣狀況: {weather_data['weather_description']}"
        response += f"\n🌅 日出時間: {weather_data['sunrise']} | 🌇 日落時間: {weather_data['sunset']}"

        # 添加天氣警告
        warning_result = self._analysis_service.check_weather_warnings(weather_data['notices'])
        warnings, rain_prob = warning_result
        for warning in warnings:
            response += f"\n{warning}"
        
        # 如果降雨機率高，推薦室內景點
        if rain_prob >= 30:
            indoor_spots = self._recommend_indoor_spots(weather_data['city'], rain_prob)
            response += f"\n🌧 {indoor_spots['message']}\n\n"
            
            for i, spot in enumerate(indoor_spots['spots'], 1):
                response += f"📍 **推薦景點 {i}：{spot['name']}**\n"
                if 'opening_hours' in spot and spot['opening_hours']:
                    response += f"🕒 **開放時間：{spot['opening_hours']}**\n"
                response += "---------------------------------\n"
            
            response += "✨ 希望這些景點能讓你的行程更豐富！不論晴天或雨天，都祝你玩得開心！☔😊"
        
        return response
    
    def _find_weather_description(self, query_info: Dict[str, Any]) -> str:
        """查找指定時間和地點的天氣描述"""
        city = query_info['台灣縣市']
        district = query_info.get('鄉鎮市區')
        date = query_info['日期']
        time = query_info['時間']

        # 檢查日期是否超過3天
        target_date = datetime.strptime(date, "%Y-%m-%d")
        current_date = datetime.now()
        week_bool = (target_date - current_date).days > 3
        
        # 獲取天氣預報數據 (使用緩存版的WeatherService)
        weather_data = self._weather_service.get_weather_forecast(city, district, week_bool)
        
        if not weather_data:
            return "無法獲取天氣數據"
        
        # 在數據中查找區域
        district_index = -1
        if district:
            for i, location in enumerate(weather_data['records']['Locations'][0]['Location']):
                if location['LocationName'] == district:
                    district_index = i
                    break
        else:
            for i, location in enumerate(weather_data['records']['Locations'][0]['Location']):
                if location['LocationName'] == city or location['LocationName'] == city.replace("台", "臺"):
                    district_index = i
                    break
                
        if district_index == -1:
            return "找不到指定的行政區"
        
        # 獲取時間數據
        time_data = weather_data['records']['Locations'][0]['Location'][district_index]['WeatherElement'][-1]['Time']
        
        # 將目標時間轉換為datetime
        target_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        # 搜索匹配的時間間隔
        for interval in time_data:
            start_time = datetime.strptime(interval['StartTime'], "%Y-%m-%dT%H:%M:%S+08:00")
            end_time = datetime.strptime(interval['EndTime'], "%Y-%m-%dT%H:%M:%S+08:00")
            
            if start_time <= target_datetime <= end_time:
                return interval['ElementValue'][0]['WeatherDescription']
        
        # 處理邊緣情況
        first_start_time = datetime.strptime(time_data[0]['StartTime'], "%Y-%m-%dT%H:%M:%S+08:00")
        last_end_time = datetime.strptime(time_data[-1]['EndTime'], "%Y-%m-%dT%H:%M:%S+08:00")
        
        # 檢查是否在第一個數據的3小時內
        if first_start_time - timedelta(hours=3) <= target_datetime < first_start_time:
            return time_data[0]['ElementValue'][0]['WeatherDescription']
        
        # 檢查是否在最後一個數據的3小時內
        if last_end_time < target_datetime <= last_end_time + timedelta(hours=3):
            return time_data[-1]['ElementValue'][0]['WeatherDescription']
        
        return "找不到指定時間的天氣資料"
    
    def _recommend_indoor_spots(self, city: str, rain_probability: int) -> Dict[str, Any]:
        """根據降雨機率推薦室內景點"""
        if rain_probability < 30:
            return {"message": "降雨機率低，戶外活動適宜。", "spots": []}
        
        # 獲取室內景點
        indoor_spots = self._scenery_service.get_location_spots(city)
        
        if not indoor_spots:
            return {"message": f"無法找到{city}的室內景點資訊。", "spots": []}
        
        # 格式化回應
        if city[:2] == '基隆':
            recommended_spots = [{"name": indoor_spots[0][1], "opening_hours": indoor_spots[0][4]}]
        else:
            # 使用前三分之一評分最高的隨機樣本
            top_spots = indoor_spots[:len(indoor_spots)//3]  # 評分最高的前三分之一
            random_indices = random.sample(range(len(top_spots)), min(5, len(top_spots)//5 or 1))
            
            recommended_spots = []
            for i, idx in enumerate(random_indices, 1):
                spot = top_spots[idx]
                spot_info = {"name": spot[1], "rating": spot[8]}
                if spot[4]:  # 如果存在開放時間
                    spot_info["opening_hours"] = spot[4]
                recommended_spots.append(spot_info)
                
                if i >= 5:  # 最多5個推薦
                    break
        
        return {
            "message": f"由於{city[:2]}有降雨的可能，我幫你挑選了一些室內或適合雨天的景點，希望你會喜歡！",
            "spots": recommended_spots
        }


def create_prompt() -> str:
    """創建用於LLM的提示"""
    current_time = datetime.now()
    date = current_time.strftime("%Y-%m-%d")
    time = current_time.strftime("%H:%M")
    weekday = current_time.weekday()

    prompt = f"""你是一個台灣旅遊天氣助手。請根據用戶的查詢提供結構化的天氣資訊。

今天日期 : {date}
現在時間 : {time}
今天星期幾 : {weekday+1}
任務說明:
1. 從用戶輸入中識別出目的地以及日期和時間
2. 判斷用戶是否在查詢單一時間點的天氣，或是查詢多日旅程的天氣趨勢
3. 如果是多日查詢，請識別出開始日期和結束日期
4. 如果沒有明確結束日期，就以開始日期+3天作為結束日期
4. 如果沒有明確指定日期使用 {date}
5. 如果沒有明確指定時間使用 {time}
6. 時間格式規範:
- 時間必須使用24小時制的"HH:MM"格式
- 小時必須是兩位數(00-23)
- 分鐘必須是兩位數(00-59)
- 小時和分鐘之間使用冒號(:)分隔
- 例如: "08:30", "14:45", "23:15"

7. 輸出格式必須是以下JSON格式的中文回答，禁止額外輸出:
A. 單日查詢:
{{
    "查詢類型": "單日",
    "地點": "目的地",
    "日期": "YYYY-MM-DD",
    "時間": "HH:MM"
}}

B. 多日查詢:
{{
    "查詢類型": "多日",
    "地點": "目的地",
    "開始日期": "YYYY-MM-DD",
    "結束日期": "YYYY-MM-DD"
}}

"""
    return prompt

def clean_llm_response(response_text: str) -> str:
    """清理 LLM 回應，提取純 JSON 字串"""
    # 使用正則表達式匹配 JSON 內容
    # 這將匹配 ```json 和 ``` 之間的內容，或直接匹配 JSON 物件
    json_pattern = r'```json\s*(.*?)\s*```|^{\s*".*?}\s*$'
    match = re.search(json_pattern, response_text, re.DOTALL)
    
    if match:
        # 如果找到匹配，返回第一個捕獲組（JSON 內容）
        json_str = match.group(1) if match.group(1) else match.group(0)
        # 移除可能的空白字符
        json_str = json_str.strip()
        return json_str
    else:
        raise ValueError(f"無法從回應中提取 JSON: {response_text}")

def llm_api(query: str, history_messages: list) -> Dict[str, Any]:
    """使用LLM API解析用戶查詢"""
    prompt = create_prompt()
    messages = history_messages[:-1] + [{"role": "system", "content": prompt}, {"role":"user", "content":query}]
    response = litellm.completion(
                api_key='ollama',
                api_base = LLM_BASE_URL,
                model=f"{API_TYPE}/{MODEL}",
                messages=messages,
                temperature=0.2, 
                max_tokens=150
            )
    response_text = clean_llm_response(response.choices[0].message.content)
    return json.loads(response_text)

def display_weather_trend(forecast_data: List[Dict[str, Any]]) -> str:
    """在ASCII格式中顯示多日天氣趨勢"""
    output = "\n==== 未來天氣趨勢 ===="
    
    # 顯示日期標頭
    date_header = " " * 10
    for day in forecast_data:
        date_header += f"{day['日期'][5:]} "
    output += f"\n{date_header}"
    
    # 顯示天氣圖示
    weather_icons = " " * 10
    for day in forecast_data:
        if "晴" in day['天氣現象']:
            weather_icons += " ☀️   "
        elif "雨" in day['天氣現象']:
            weather_icons += " 🌧️   "
        elif "陰" in day['天氣現象']:
            weather_icons += " ☁️   "
        else:
            weather_icons += " 🌤️   "
    output += f"\n{weather_icons}"
    
    # 顯示溫度
    temp_line = "溫度(°C): "
    for day in forecast_data:
        temp_line += f" {day['平均溫度']:2d}°  "
    output += f"\n{temp_line}"
    
    # 顯示降雨機率
    rain_line = "降雨(%):  "
    for day in forecast_data:
        if not isinstance(day['降雨機率'], str):
            rain_line += f" {day['降雨機率']:2d}%  "
        else:
            rain_line += f"  -   "
    output += f"\n{rain_line}"
    
    # 顯示戶外適宜度
    suitability_line = "戶外適宜: "
    for day in forecast_data:
        if day['適宜度分數'] > 80:
            suitability_line += " 👍  "
        elif day['適宜度分數'] > 60:
            suitability_line += " 🙂  "
        elif day['適宜度分數'] > 40:
            suitability_line += " 😐  "
        else:
            suitability_line += " 👎  "
    output += f"\n{suitability_line}"
    
    return output


if __name__ == "__main__":
    tool = WeatherTool()
    test_queries = ["日月潭天氣", "草屯周末天氣", '國聖燈塔4/19~4/28的天氣如何']

    for query in test_queries:
        print(f"\n測試查詢: {query}")
        result = tool._run(query,[])
        print(result)