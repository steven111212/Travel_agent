import os
import sys
import litellm
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.parking_service import ParkingService
from langchain.tools import BaseTool
from typing import Dict, List, Any, Optional, Union, Literal, ClassVar
from config import LLM_BASE_URL, API_TYPE, MODEL, LLM_API_KEY

class ParkingTool(BaseTool):
    """停車場查詢工具"""

    name: ClassVar[str] = "parking_tool"
    description: ClassVar[str] = "使用 Google Maps API 獲取目的地的經緯度，並查詢目的地附近停車場資訊。"

    def __init__(self):
        super().__init__()
        self._parking_service = ParkingService()

    def _run(self, query_input: str, history_messages : list) -> str:
        """
        執行停車場資訊查詢
        
        參數:
            query_input (str): 用戶查詢輸入
                
        返回:
            str: 格式化的高速公路交通資訊回應
        """
        try:
            location = self._llm_api(query_input, history_messages)
            
            if not location or location.strip() == "":
                return "無法從您的查詢中識別出具體地點，請提供更明確的地址或地標。"
            
            parking_data = self._parking_service._get_parking_information(location)
            
            if parking_data is None or len(parking_data) == 0:
                return f"無法找到「{location}」附近的停車場資訊，請確認地址是否正確或嘗試其他地點。"
            
            # 按照距離排序（假設 API 返回的資料中有距離資訊）
            if parking_data and len(parking_data) > 0 and 'Distance' in parking_data[0]:
                parking_data.sort(key=lambda x: x.get('Distance', float('inf')))
            
            response = f"在「{location}」附近找到 {len(parking_data)} 個停車場："
            response += "\n" + "-" * 50
        

            for i, parking in enumerate(parking_data[:10], 1):
                
                name = parking.get('CarParkName', {}).get('Zh_tw', '未知')
                address = parking.get('Address', '未知')
                total_spaces = parking.get('Description', '未知')
                charge_info = parking.get('FareDescription', '未知').split('月')[0] if parking.get('FareDescription') else '未知'
                
                response += f"\n{i}. 🅿️ 名稱: {name}"
                response += f"\n   📍 地址: {address}"
                response += f"\n   🚗 總停車位: {total_spaces}"
                response += f"\n   💰 收費資訊: {charge_info}"
                response += "\n" + "-" * 50
            if len(parking_data) > 10:
                response += f"\n※ 共找到 {len(parking_data)} 筆資料，僅顯示前 10 筆最近的停車場"
        
            return response
        except Exception as e:
            return f"查詢停車場資訊時發生錯誤：{str(e)}"
        


    def _llm_api(self, query, history_messages):
        """使用LLM API解析用戶查詢，增強錯誤處理"""
       
        prompt = f"""請從以下用戶輸入中識別出具體的地點或目的地，只需回傳地點名稱，不需要其他解釋：
        用戶輸入：{query}"""
        messages = history_messages[:-1]+[{"role": "system", "content": prompt}]
        response = litellm.completion(
            api_key=LLM_API_KEY,
            api_base=LLM_BASE_URL,
            model=f"{API_TYPE}/{MODEL}",
            messages=messages,
            temperature=0.1
        )
        response_text = response.choices[0].message.content

        return response_text
    

if __name__ == "__main__":
    parking_tool = ParkingTool()
    query_input = "請問大稻埕附近的停車場"
    response = parking_tool._run(query_input)
    print(response)
            
                
            