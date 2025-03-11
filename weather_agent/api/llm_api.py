from openai import OpenAI
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LLM_API_KEY, LLM_BASE_URL
from utils import clean_llm_response  # 注意這裡

class llmAPI:
    """語言模型 API 封裝"""
    
    def __init__(self):
        self.api_key = LLM_API_KEY
        self.base_url = LLM_BASE_URL
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def query(self, prompt, model="yentinglin/Llama-3-Taiwan-8B-Instruct", temperature=0.2):
        """向LLM提交查詢"""
        messages=[{"role":"system","content":prompt}]
        response = self.client.chat.completions.create(
            model=model,
            messages=messages, 
            temperature=temperature, 
            max_tokens=500, 
            frequency_penalty=0.2
        )
        # 解析並返回結果
        response_content = response.choices[0].message.content
        cleaned_json = clean_llm_response(response_content)
        return cleaned_json