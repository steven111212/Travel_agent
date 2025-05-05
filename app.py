from flask import Flask, request, jsonify, render_template
import os
import sys
import time

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the main travel assistant class
from graphs.orchestrator_graph import TravelAssistant

# Create Flask app
app = Flask(__name__)

# Initialize the travel assistant
travel_assistant = TravelAssistant()

@app.route('/')
def index():
    """Render the main page"""
    return render_template('travel_agent.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        # Get user input
        data = request.json
        user_message = data.get('message', '')
        
        if not user_message:
            return jsonify({'response': '請輸入訊息'})
        
        # 記錄開始處理時間
        start_time = time.time()
        
        # Process the query through the travel assistant
        result = travel_assistant.process_query(user_message)
        
        # 計算處理時間
        elapsed_time = time.time() - start_time
        print(f"處理時間: {elapsed_time:.2f}秒")
        
        return jsonify({
            'response': result['response'],
            'history': result['history']
        })
                
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({'response': f'發生錯誤: {str(e)}'})
    
@app.route('/clear_history', methods=['POST'])
def clear_history():
    """清除對話歷史"""
    try:
        travel_assistant.clear_chat_history()
        return jsonify({'status': 'success', 'message': '對話歷史已清除'})
    except Exception as e:
        print(f"Error clearing history: {str(e)}")
        return jsonify({'status': 'error', 'message': f'清除歷史時發生錯誤: {str(e)}'})

# 確保 JS 檔案可以被正確提供
@app.route('/static/<path:filename>')
def serve_static(filename):
    return app.send_static_file(filename)

if __name__ == '__main__':
    # Start Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)