from openai import OpenAI
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LLM_BASE_URL, API_TYPE, MODEL
from utils import clean_llm_response  # 注意這裡
import litellm


class llmAPI:
    """語言模型 API 封裝"""
    
    def __init__(self):

        self.model = f"{API_TYPE}/{MODEL}"
        self.base_url = LLM_BASE_URL
    
    def query(self, prompt, temperature=0.2):
        """向LLM提交查詢"""
        messages=[{"role":"system","content":prompt}]
        response = litellm.completion(
            api_base = self.base_url,
            model=self.model,
            messages=messages, 
            temperature=temperature, 
            max_tokens=500
        )
        # 解析並返回結果
        response_content = response.choices[0].message.content
        print(response_content)
        cleaned_json = clean_llm_response(response_content)
        return cleaned_json
    
    def query_intent(self, user_message):
        intent_messages = [
            {"role": "system", "content": "你是一個意圖分析助手，你的任務是判斷用戶是否想知道天氣信息。請回答'是'或'否'。"},
            {"role": "user", "content": user_message}
        ]
        
        intent_response = litellm.completion(
            api_base = self.base_url,
            api_key = 'ollama',
            model=self.model,
            messages=intent_messages,
        )
        
        return intent_response.choices[0].message.content.strip().lower()
    
    def query_general(self, user_message):

        chat_messages = [
                {"role": "system", "content": "你是個旅遊助手，你會回答用戶在旅遊的問題，請用繁體中文回答，嚴格禁止使用任何簡體中文回答。"},
                {"role": "user", "content": user_message}]
        llm_response = litellm.completion(
            api_base = self.base_url,
            api_key = 'ollama',
            model=self.model,
            messages=chat_messages,
        )
        response_content = llm_response.choices[0].message.content

        return response_content
