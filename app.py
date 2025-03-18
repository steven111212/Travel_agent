from flask import Flask, request, jsonify, render_template
from openai import OpenAI
import os
import sys
from transportation_agent import transportation_agent
from transportation_agent import llm_transportation
# 將 weather_agent 目錄添加到 Python 路徑
sys.path.append(os.path.join(os.path.dirname(__file__), 'weather_agent'))
from weather_agent.main import weather_agent
from weather_agent.api import llmAPI
from config import LLM_BASE_URL, API_TYPE, MODEL

# 初始化LLM客戶端
# llm = OpenAI(
#     api_key='ollama',
#     base_url="http://172.16.111.30:18187/v1"
# )
app = Flask(__name__)
print(LLM_BASE_URL,API_TYPE, MODEL)
model = f"{API_TYPE}/{MODEL}"


@app.route('/')
def index():
    return render_template('travel_agent.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # 獲取用戶輸入
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'response': '請輸入訊息'})
        
        # 初始化回應內容和標記
        final_response = ""
        has_response = False
        
        # 分析用戶意圖
        weather_llm = llmAPI()
        weather_intent_result = weather_llm.query_intent(user_message)
        
        # 如果用戶想了解天氣，調用天氣agent
        if '是' in weather_intent_result:
            weather_response = weather_agent(user_message)
            final_response += weather_response
            has_response = True
            
        # 判斷是否為交通查詢
        transportation_llm = llm_transportation()
        transportation_intent_result = transportation_llm.query_intent(user_message)

        # 如果是交通查詢，使用交通agent
        if '是' in transportation_intent_result:
            transportation_response = transportation_agent(user_message)
            # 如果已經有天氣回應，添加分隔符
            if has_response:
                final_response += "\n\n" + "="*30 + "\n\n"
            final_response += transportation_response

            print(transportation_response)
            has_response = True

        # 如果都不是，使用一般LLM回應
        if not has_response:
            final_response = weather_llm.query_general(user_message)

        return jsonify({'response': final_response})
                
    except Exception as e:
        return jsonify({'response': f'發生錯誤: {str(e)}'})

if __name__ == '__main__':

    # 啟動Flask應用
    app.run(debug=True, host='0.0.0.0', port=5000)