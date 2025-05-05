import sys
import os
import json
from typing import Dict, List, Any, Optional, Union, Literal, ClassVar
import litellm
import re
import random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.nearby_service import NearbyService
from langchain.tools import BaseTool
from config import LLM_BASE_URL, API_TYPE, MODEL, LLM_API_KEY

class NearbyTool(BaseTool):
    """搜尋附近的商家或地點"""

    name: ClassVar[str] = "nearby_tool"

    description: ClassVar[str] = """這個工具可以查詢特定地點附近的美食、景點、咖啡廳等。
適用場景:
- 用戶想要了解特定地點附近的商家或景點

"""

    def __init__(self):
        super().__init__()
        self._nearby_service = NearbyService()

    def _run(self, query_input: str, history_messages: list) -> str:
        try:
            # 使用 LLM API 解析查詢
            query_info = self._llm_api(query_input, history_messages)
            # 正常回傳json格式，如果是字串則直接回傳
            if isinstance(query_info, str):
                return query_info
            # 提取地點和關鍵字
            result = self._nearby_service._get_nearby_places(query_info['location'], query_info['keyword'])

            return self._format_places_response(result, sample_n=5)

        except Exception as e:
            print(f"錯誤發生: {str(e)}")
            return f"搜尋過程中發生錯誤：{str(e)}，請稍後再試或修改您的查詢。"
        
    def _format_places_response(self, places_data, sample_n: int = 5) -> str:
        """格式化餐廳搜尋結果的回應文字"""
        response = "\n🔍 查詢結果如下：\n"

        # 條件過濾：符合下列任一條件
        filtered = [
            place for place in places_data
            if (place.get("user_ratings_total", 0) > 500 and place.get("rating", 0) > 4.0) or
            (place.get("user_ratings_total", 0) > 100 and place.get("rating", 0) > 4.5)
        ]

        # 如果過濾後的數量少於 10 筆，則使用原始資料
        if len(filtered) <= 10:
            filtered = places_data

        # 隨機挑選（最多 sample_n 筆）
        selected = random.sample(filtered, k=min(sample_n, len(filtered)))

        for i, place in enumerate(selected, 1):
            name = place.get("name", "無名稱")
            address = place.get("vicinity", "無地址")
            rating = place.get("rating", "無評分")
            total_ratings = place.get("user_ratings_total", 0)
            is_open = place.get("opening_hours", {}).get("open_now", None)
            open_status = "🟢 營業中" if is_open else ("🔴 未營業" if is_open is not None else "⚪ 無營業資訊")
            
            response += f"\n📍 推薦地點 {i}：{name}"
            response += f"\n📌 地址：{address}"
            response += f"\n⭐ 評分：{rating}（{total_ratings} 則評論）"
            response += f"\n⏰ 營業狀態：{open_status}"
            response += "\n---------------------------------------"

        if not selected:
            response += "\n😢 找不到符合條件的餐廳，請試試更大的範圍或不同關鍵字。"
        else:
            response += "\n✨ 希望這些推薦能讓你的用餐體驗更棒！🍜🍰☕"

        return response


    def _llm_api(self, query, history_messages):

        try:
            prompt = self._create_prompt()
            messages = history_messages[:-1] + [{"role": "system", "content": prompt}, {"role":"user", "content":query}]
            response = litellm.completion(
                api_key=LLM_API_KEY,
                api_base=LLM_BASE_URL,
                model=f"{API_TYPE}/{MODEL}",
                messages=messages,
                temperature=0.2
            )
            response_text = response.choices[0].message.content
            cleaned_response = self._clean_llm_response(response_text)
            query_info = json.loads(cleaned_response)
            if 'location' not in query_info or 'keyword' not in query_info:
                return '無法識別提問的關鍵字或地點，請重新輸入'
            if query_info['location'] is None or query_info['keyword'] is None:
                return '無法識別提問的關鍵字或地點，請重新輸入'
            
            return query_info
        
        except Exception as e:
            print(f"LLM API 錯誤: {str(e)}")
            return '無法識別提問的問題，請重新輸入'

    def _create_prompt(self):
        prompt = f"""你是一個專門識別用戶查詢意圖的助手。你的任務是從用戶的自然語言輸入中，準確提取出兩個關鍵信息：
    1. 用戶想搜尋的地理位置
    2. 用戶想搜尋的商家類型或關鍵字

    無論用戶的輸入多麼隨意或複雜，你都需要理解並識別出這兩個核心要素。

    規則：
    - 如果用戶完全未提及地點，location應為null
    - 如果用戶未明確指定商家類型或關鍵字，keyword應為null
    - 只提取實際位置名稱，不要包含「附近」、「周邊」等修飾詞
    - 台灣的地名使用當地通用名稱，如「台北」而非「Taipei」

    請以JSON格式回覆，不要有任何前導或後接文字：
    {{
    "location": "欲查詢的地點",
    "keyword": "欲查詢的商家或關鍵字"
    }}
    """
        return prompt
    
    def _clean_llm_response(self, response_text):
        """清理 LLM 回應，提取純 JSON 字串"""
        try:
            # 直接嘗試解析整個回應
            json_obj = json.loads(response_text)
            return json.dumps(json_obj)
        except json.JSONDecodeError:
            # 如果直接解析失敗，嘗試提取 JSON 部分
            try:
                # 尋找 JSON 物件的開始和結束
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}') + 1
                
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response_text[start_idx:end_idx]
                    # 驗證提取的字串是否為有效的 JSON
                    json_obj = json.loads(json_str)
                    return json.dumps(json_obj)
                else:
                    # 嘗試另一種方式：尋找 ```json 標記
                    json_block_pattern = r'```(?:json)?\s*({.*?})\s*```'
                    match = re.search(json_block_pattern, response_text, re.DOTALL)
                    if match:
                        json_str = match.group(1)
                        json_obj = json.loads(json_str)
                        return json.dumps(json_obj)
                    else:
                        raise ValueError("無法找到有效的 JSON 格式")
            except Exception as e:
                raise ValueError(f"無法從回應中提取 JSON: {str(e)}")
            
if __name__ == "__main__":
    tool = NearbyTool()
    query = "台北市信義區附近有什麼好吃的?"
    result = tool._run(query, [])
    print(result)