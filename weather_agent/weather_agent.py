from datetime import datetime, timedelta
import json
from openai import OpenAI
import requests
import re
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherQuery:
    def __init__(self):
        """初始化天氣查詢處理器"""
        self.llm = OpenAI(
            api_key='None',
            base_url="http://172.16.1.18:18501/v1"
        )
    def find_weather_description(self, LLM_response) -> str:

        try:
            #在天氣資料中找出指定行政區的資料
            week_bool = check_time_difference(LLM_response)  #檢查天數是否超過3天
            weather_data = self.get_weather_forecast(LLM_response['台灣縣市'], week_bool)
            if not weather_data:
                    return "無法獲取天氣數據"
            district_index = -1
            for i, location in enumerate(weather_data['records']['Locations'][0]['Location']):
                if location['LocationName'] == LLM_response['鄉鎮市區']:
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
    def get_sunrise_data(self, result):

        base_url = "https://opendata.cwa.gov.tw/api"
        
        # API 端點路徑 (從圖片中可以看到的預報API路徑)
        endpoint = "/v1/rest/datastore/A-B0062-001"  # 一般天氣預報-今明 36 小時天氣預報
        
        # 你需要一個 API 授權金鑰
        api_key = ""
        
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

    def get_weather_forecast(self, city, week=False):
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
        
        # API 端點路徑
        endpoint = "/v1/rest/datastore/F-D0047-"+city_code[city]  # 一般天氣預報-今明 36 小時天氣預報
        
        api_key = ""
        
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

    def query_weather(self, user_query):
        """處理用戶的天氣查詢"""
        try:
            # 生成prompt並查詢LLM
            prompt = create_prompt(user_query)
            messages=[{"role":"system","content":prompt}]
            response = self.llm.chat.completions.create(
                    model="yentinglin/Llama-3-Taiwan-8B-Instruct",
                    messages=messages, temperature=0.2, max_tokens=500, frequency_penalty=0.2
                )
            # 解析並返回結果
            response_content = response.choices[0].message.content
            cleaned_json = clean_llm_response(response_content)
            return json.loads(cleaned_json)
            
        except Exception as e:
            logger.error(f"LLM查詢失敗: {e}")
            raise Exception(f"處理查詢時發生錯誤: {str(e)}")
        
def check_time_difference(result):
    # 將 result 中的日期和時間合併並轉換為 datetime 物件
    result_datetime_str = f"{result['日期']} {result['時間']}"
    result_datetime = datetime.strptime(result_datetime_str, '%Y-%m-%d %H:%M')
    
    # 計算時間差
    time_difference = result_datetime - datetime.now()
    
    # 檢查是否超過 3 天
    return time_difference.days >= 3

def get_default_time():
    """獲取預設的時間和日期(當前時間+1小時)"""
    current_time = datetime.now()
    default_time = current_time 
    return {
        "date": default_time.strftime("%Y-%m-%d"),
        "time": default_time.strftime("%H%M")
    }

def create_prompt(query):
    """生成用於LLM的prompt"""
    default_time = get_default_time()
    
    prompt = f"""你是一個台灣旅遊天氣助手。請根據用戶的查詢提供結構化的天氣資訊。

今天日期 : {default_time['date']}
現在時間 : {default_time['time']}
任務說明:
1. 從用戶輸入中識別出目的地以及目的地所在縣市和地區、日期和時間
2. 如果沒有明確指定日期使用 {default_time['date']}
3. 如果沒有明確指定時間使用 {default_time['time']}
4. 需要判斷地標或景點所在的確切行政區
5. 時間格式規範:
   - 時間必須使用24小時制的"HH:MM"格式
   - 小時必須是兩位數(00-23)
   - 分鐘必須是兩位數(00-59)
   - 小時和分鐘之間使用冒號(:)分隔
   - 例如: "08:30", "14:45", "23:15"
6. 如果用戶沒有指定鄉鎮市區，則使用該縣市最大的鄉鎮市區
7. 輸出格式必須是以下JSON格式的中文回答:
    {{
        "台灣縣市": "二級行政區名稱",
        "鄉鎮市區": "三級行政區名稱",
        "日期": "YYYY-MM-DD",
        "時間": "HH:MM"
    }}

{query}
"""
    return prompt

def format_time(time_str):
    """格式化時間字串"""
    if ":" not in time_str:
        # 清理並補零
        numbers = ''.join(filter(str.isdigit, time_str)).zfill(4)
        return numbers[0:2] + ":" + numbers[2:4]
    return time_str
    
    
def clean_llm_response(response_text):
    """清理 LLM 回應，提取純 JSON 字串"""
    # 使用正則表達式匹配 JSON 內容
    # 這將匹配 ```json 和 ``` 之間的內容，或直接匹配 JSON 物件
    json_pattern = r'```json\s*({.*?})\s*```|^{\s*".*?}\s*$'
    match = re.search(json_pattern, response_text, re.DOTALL)
    
    if match:
        # 如果找到匹配，返回第一個捕獲組（JSON 內容）
        json_str = match.group(1) if match.group(1) else match.group(0)
        # 移除可能的空白字符
        json_str = json_str.strip()
        return json_str
    else:
        raise ValueError(f"無法從回應中提取 JSON: {response_text}")
    
def run_interactive_weather_query():
    """執行互動式天氣查詢對話"""
    print("\n=== 歡迎使用台灣旅遊天氣助手 ===")
    print("請輸入您想查詢的地點和時間")
    print("輸入 'stop' 結束對話\n")
    
    # 創建查詢處理器實例
    handler = WeatherQuery()
    
    while True:
        try:
            # 獲取用戶輸入
            user_input = input("請問您想查詢哪裡的天氣？ ").strip()
            
            # 檢查是否要結束對話
            if user_input.lower() == 'stop':
                print("\n謝謝使用，再見！")
                break
            
            # 檢查是否有輸入內容
            if not user_input:
                print("請輸入查詢內容")
                continue
            
            # 處理查詢
            result = handler.query_weather(user_input)
            result['時間'] = format_time(result['時間'])  #時間格式處理
            print(result)
            if "台" in result["台灣縣市"]:
                result["台灣縣市"] = result["台灣縣市"].replace("台", "臺")
            weather_desc = handler.find_weather_description(result)
            sunrise_data = handler.get_sunrise_data(result)
            # 輸出結果
            print(f"\n查詢結果:")
            print(f"地點: {result['台灣縣市']}{result['鄉鎮市區']}")
            print(f"時間: {result['日期']} {result['時間']}")
            print(f"天氣狀況: {weather_desc}")
            print(f"日出時間:{sunrise_data['SunRiseTime']}")
            print(f"日落時間:{sunrise_data['SunSetTime']}")
            print("-----------------------------------------------------------")
            
        except Exception as e:
            print(f"抱歉，查詢過程中發生錯誤: {str(e)}")
            print("請重新輸入查詢\n")

if __name__ == "__main__":
    # try:
    #     # 創建處理器實例
    #     handler = WeatherQuery()
        
    #     # 測試查詢
    #     query = "我想去台北"
    #     result = handler.query_weather(query)
    #     print(f"查詢結果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    #     print(handler.find_weather_description(result['台灣縣市'], result['鄉鎮市區'], result['日期'], result['時間']))
    # except Exception as e:
    #     print(f"錯誤: {str(e)}")
    run_interactive_weather_query()