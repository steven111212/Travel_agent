import sys
import os
import litellm
import re
# 添加專案根目錄到Python路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LLM_BASE_URL, API_TYPE, MODEL

class llm_transportation:
    def query_intent(self, user_message):
        """
        判斷用戶訊息是否與交通相關
        
        Args:
            user_message (str): 用戶輸入的訊息
        
        Returns:
            str: "是" 或 "否"
        """
        prompt = f"""
        請判斷以下用戶訊息是否與交通或路線規劃相關：
        
        用戶訊息: {user_message}
        
        如果用戶訊息涉及以下任何內容，請回答"是"，否則回答"否"：
        - 詢問如何從一個地方到另一個地方
        
        只需回答"是"或"否"，不需要解釋。
        """
        # - 詢問交通工具（如汽車、公車、捷運、計程車、火車、高鐵等）
        # - 詢問路線、票價或時間表
        # - 詢問最快/最便宜/最方便的交通方式
        # - 詢問交通站點、車站、景點或地標
        # - 提及需要交通建議或路線規劃
        # - 提及景點遊覽順序或多點行程規劃
        try:

            messages=[
                    {"role": "system", "content": "你是一個專門判斷用戶意圖的助手。"},
                    {"role": "user", "content": prompt}]
            temperature=0.1
            max_tokens=50
            response = transportation_llm_api(messages, max_tokens, temperature)
            
            return response
            
        except Exception as e:
            print(f"判斷意圖時出錯: {str(e)}")
            return "否"  # 發生錯誤時，默認不是交通相關
    
    def query_general(self, user_message):
        """
        處理一般非特定領域的查詢
        
        Args:
            user_message (str): 用戶輸入的訊息
        
        Returns:
            str: LLM的回應
        """
        try:
            messages=[
                {"role": "system", "content": "你是一個友善的旅遊助手，可以回答各種旅遊相關問題。"},
                    {"role": "user", "content": user_message}
                        ]
            temperature=0.7
            max_tokens=800
            response = transportation_llm_api(messages, max_tokens, temperature)
        
            return response
            
        except Exception as e:
            print(f"一般查詢時出錯: {str(e)}")
            return f"抱歉，處理您的查詢時發生錯誤: {str(e)}"

        

def transportation_llm_api(messages, max_tokens, temperature):
    response = litellm.completion(
                api_key='ollama',
                api_base = LLM_BASE_URL,
                model=f"{API_TYPE}/{MODEL}",
                messages=messages,
                temperature=temperature, 
                max_tokens=max_tokens
            )
    
    return response.choices[0].message.content