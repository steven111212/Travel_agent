import os
import sys
import litellm
from langchain.tools import BaseTool
from typing import ClassVar
from config import LLM_BASE_URL, API_TYPE, MODEL, LLM_API_KEY

class GeneralTool(BaseTool):
    """通用工具類"""

    name: ClassVar[str] = "general_tool"
    description: ClassVar[str] = "通用工具類，用於回答一般性的旅遊問題。"

    def __init__(self):
        super().__init__()
        
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
            system_prompt = """你是一個友善的旅遊助手，可以回答各種旅遊相關問題。

你應該能夠提供關於以下主題的資訊和建議：
- 台灣的旅遊景點和特色
- 當地美食和特產
- 旅遊季節和最佳時間
- 文化習俗和禮儀
- 旅遊預算建議
- 行李打包建議
- 安全提示

請使用繁體中文回應，詳細解說旅遊相關主題，並提供具體且實用的建議。
保持友善、有禮的語氣，讓用戶感到你真的想幫助他們。

如果問題涉及台灣的景點、文化、美食、活動或住宿，請盡可能提供深入的回答和實用的建議。
如果問題不清楚或太寬泛，可以提供一般性的旅遊建議或反問來澄清用戶的需求。
"""

            messages = history_messages[:-1]+[{"role": "system", "content": system_prompt},
                        {"role": "user", "content": query}]
            
            response = litellm.completion(
            api_key=LLM_API_KEY,
            api_base=LLM_BASE_URL,
            model=f"{API_TYPE}/{MODEL}",
            messages=messages,
            temperature=0.1
        )
            response_text = response.choices[0].message.content
            return response_text
        
        except Exception as e:
            return f"發生錯誤: {str(e)}"


if __name__ == "__main__":
    tool = GeneralTool()
    query_input = "請問台北101附近有什麼好吃的餐廳？"
    response = tool._run(query_input)
    print(response)