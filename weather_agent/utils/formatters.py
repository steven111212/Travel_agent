import re
import json
from datetime import datetime, timedelta

def check_time_difference(result):
    # 將 result 中的日期和時間合併並轉換為 datetime 物件
    result_datetime_str = f"{result['日期']} {result['時間']}"
    result_datetime = datetime.strptime(result_datetime_str, '%Y-%m-%d %H:%M')
    
    # 計算時間差
    time_difference = result_datetime - datetime.now()
    
    # 檢查是否超過 3 天
    return time_difference.days >= 3

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

def get_default_time():
    """獲取預設的時間和日期(當前時間+1小時)"""
    current_time = datetime.now()
    default_time = current_time 
    return {
        "date": default_time.strftime("%Y-%m-%d"),
        "time": default_time.strftime("%H%M")
    }

def format_time(time_str):
    """格式化時間字串"""
    if ":" not in time_str:
        # 清理並補零
        numbers = ''.join(filter(str.isdigit, time_str)).zfill(4)
        return numbers[0:2] + ":" + numbers[2:4]
    return time_str

def create_prompt(query):
    """生成用於LLM的prompt"""
    default_time = get_default_time()
    
    prompt = f"""你是一個台灣旅遊天氣助手。請根據用戶的查詢提供結構化的天氣資訊。

今天日期 : {default_time['date']}
現在時間 : {default_time['time']}
任務說明:
1. 從用戶輸入中識別出目的地以及日期和時間
2. 判斷用戶是否在查詢單一時間點的天氣，或是查詢多日旅程的天氣趨勢
3. 如果是多日查詢，請識別出開始日期和結束日期
4. 如果沒有明確指定日期使用 {default_time['date']}
5. 如果沒有明確指定時間使用 {default_time['time']}
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

{query}
"""
    return prompt
