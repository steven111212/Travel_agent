from langchain.tools import BaseTool
from typing import ClassVar
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from openai import OpenAI

class ScheduleTool(BaseTool):
    """通用工具類"""

    name: ClassVar[str] = "schedule_tool"
    description: ClassVar[str] = "旅遊行程規劃工具，用於回答行程規劃的旅遊問題。"

    def __init__(self):
        super().__init__()
        self._llm = OpenAI(api_key='sk-56d9f30fdee64135abcfaaee7b34080a', base_url='https://api.deepseek.com')

    def _run(self, query_input: str, history_messages : list) -> str:
        """
        執行通用查詢
        參數:
            query_input (str): 用戶查詢輸入
                
        返回:
            str: 格式化的查詢回應
        """
        response = self._llm_api(query_input, history_messages)
        return response
    
    def _llm_api(self, query, history_messages):
        """使用LLM API解析用戶查詢，增強錯誤處理"""
        try:
            system_prompt = """你現在是一位專業的旅遊規劃師，具備豐富的台灣旅遊知識，你會簡要的幫用戶快速規畫適合的行程，回答時保持結構乾淨有條理，避免重複冗詞。
"""  
#             system_prompt = """你是「台灣行程規劃專家」，一個專精於台灣本島旅遊規劃的AI助手。你具備豐富的台灣地理、交通、文化、美食和旅遊資源知識，能夠為不同需求的旅客提供客製化行程建議。

# 針對每個行程建議，可以提供：
# 1. 整體行程概述
# """  
# 2. 景點推薦
# 3. 交通建議與注意事項
# 4. 住宿建議
# 5. 當地特色美食推薦
# 6. 季節性考量（天氣、節慶活動）
# 7. 實用的在地小技巧和文化提示       
            messages = history_messages[:-1]+[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}]
            response = self._llm.chat.completions.create(model= 'deepseek-chat',
                                                        messages=messages, 
                                                        temperature=0.5)
            response_text = response.choices[0].message.content
            return response_text
        
        except Exception as e:
            return f"發生錯誤: {str(e)}"


if __name__ == "__main__":
    tool = ScheduleTool()
    query_input = "安排三天兩夜的花東之旅"
    response = tool._run(query_input, [])
    print(response)