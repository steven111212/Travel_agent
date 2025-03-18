import sys
import os
import json
import re
from transportation_agent.route_planner import TravelRoutePlanner
from transportation_agent.api import transportation_llm_api
# 添加專案根目錄到Python路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LLM_BASE_URL, API_TYPE, MODEL, GOOGLE_MAPS_API_KEY

def transportation_agent(user_message):
    """
    處理與交通相關的查詢
    
    Args:
        user_message (str): 用戶輸入的訊息
    
    Returns:
        str: 回應用戶的交通相關訊息
    """
    # 初始化旅遊路線規劃器
    planner = TravelRoutePlanner(
        google_maps_api_key=GOOGLE_MAPS_API_KEY,
    )
    
    # 解析用戶查詢內容
    route_info = parse_route_query(user_message)
    print(route_info)
    # 根據解析結果提供路線建議
    if route_info['mode'] == 'driving' and route_info['attractions']:
        # 多景點模式 (A到B經過C,D,E)
        routes = planner.get_optimized_multi_stop_route(
            route_info['origin'], 
            route_info['destination'], 
            route_info['attractions']
        )
        return format_multi_stop_response(routes)
        
    elif route_info['mode'] == 'transit':
        # 大眾運輸模式
        routes = planner.get_transit_routes(
            route_info['origin'], 
            route_info['destination']
        )
        return format_transit_response(routes)
        
    else:
        # 一般駕車模式 (A到B)
        routes = planner.get_driving_routes(
            route_info['origin'], 
            route_info['destination']
        )
        return format_driving_response(routes)

def parse_route_query(user_message):
    """
    解析用戶的路線查詢
    
    Args:
        planner: 路線規劃器實例
        user_message (str): 用戶輸入的訊息
    
    Returns:
        dict: 解析後的路線信息
    """
    prompt = f"""您的任務是識別用戶旅遊查詢中的關鍵資訊，並將其轉換為結構化的JSON格式。

輸入分析要求
分析用戶的輸入查詢，識別以下關鍵資訊：

出發地 (origin) - 必須識別
目的地 (destination) - 必須識別
交通方式 (mode) - 重要：預設為"driving"（開車）

交通方式判斷規則：
- 若用戶沒有明確提及交通方式，一律設為"driving"
- 僅當用戶明確提到搭乘大眾運輸工具（如公車、捷運、火車、高鐵等）時，才設為"transit"
- 單純提及多個景點或中途停留點，不代表使用公共交通

沿途景點 (attractions) - 如果提到，加入清單；若未提到，則為空清單

輸出格式
必須以下列JSON格式返回結果：
{{
  "origin": "出發地點",
  "destination": "目的地點",
  "mode": "交通方式",
  "attractions": ["景點1", "景點2", ...]
}}

{user_message}
"""
    messages = [{"role": "system", "content": prompt}]
    try:
        response = transportation_llm_api(messages, max_tokens=500, temperature=0.2)
        response = clean_llm_response(response)
        result = json.loads(response)
        return result
    except Exception as e:
        print(f"解析查詢時出錯: {str(e)}")
        # 返回默認值
        return {
            "origin": "未能識別出發地",
            "destination": "未能識別目的地",
            "mode": "driving",
            "attractions": []
        }
    
        
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

def format_driving_response(routes):
    """
    格式化駕車路線的輸出
    
    Args:
        routes (list): 包含路線信息的列表
    
    Returns:
        str: 格式化後的回應
    """
    if not routes:
        return "抱歉，無法獲取駕車路線信息。"
    
    # 最多顯示2條路線
    routes = routes[:2]
    
    response = "📍 駕車路線建議\n"
    response += "==================\n\n"
    
    for route in routes:
        response += f"🚗 路線 {route['route_number']}: {route['summary']}\n"
        response += f"從: {route['origin']}\n"
        response += f"到: {route['destination']}\n"
        response += f"⏱️ 預估時間: {route['duration']}\n"
        response += f"📏 距離: {route['distance']}\n"
        response += f"🕒 預計到達時間: {route['arrival_time']}\n\n"
        
        response += "📝 簡化路線說明:\n"
        response += f"{route['simplified_route']}\n\n"
        
        response += f"🔗 Google Maps導航: {route['google_maps_url']}\n"
        response += "==================\n\n"
    
    #response += "需要更詳細的路線說明嗎？"
    
    return response

def format_transit_response(routes):
    """
    格式化大眾運輸路線的輸出
    
    Args:
        routes (list): 包含路線信息的列表
    
    Returns:
        str: 格式化後的回應
    """
    if not routes:
        return "抱歉，無法獲取大眾運輸路線信息。"
    
    response = "📍 大眾運輸路線建議\n"
    response += "==================\n\n"
    
    for route in routes:
        response += f"🚆 路線 {route['route_number']}\n"
        response += f"⏱️ 預估時間: {route['duration']}\n"
        response += f"📏 距離: {route['distance']}\n"
        response += f"🕒 出發時間: {route['departure_time']}\n"
        response += f"🕒 預計到達時間: {route['arrival_time']}\n\n"
        
        # 提取步驟信息
        lines = route['detail_route'].split('\n')
        steps = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 檢查是否為步驟行
            if line.startswith("步驟 "):
                step_number = line
                step_data = {"step": step_number, "description": "", "details": []}
                
                # 獲取步驟描述（下一行）
                if i + 1 < len(lines):
                    step_data["description"] = lines[i + 1].strip()
                
                # 獲取步驟細節
                j = i + 2
                while j < len(lines) and not lines[j].startswith("步驟 ") and lines[j].strip():
                    detail_line = lines[j].strip()
                    
                    # 收集各種詳細信息
                    if detail_line.startswith("交通方式:") or detail_line.startswith("路線:") or detail_line.startswith("上車站點:") or detail_line.startswith("下車站點:") or detail_line.startswith("車號:"):
                        step_data["details"].append(detail_line)
                    elif detail_line.startswith("時間:"):
                        step_data["time"] = detail_line
                    elif detail_line.startswith("距離:"):
                        step_data["distance"] = detail_line
                        
                    j += 1
                
                steps.append(step_data)
                i = j  # 跳到下一個步驟或空行
            else:
                i += 1
        
        # 構建步驟輸出
        response += "📝 路線步驟:\n"
        for step_data in steps:
            step_info = f"{step_data['step']}: {step_data['description']}"
            
            # 添加時間和距離
            if "time" in step_data:
                step_info += f" | {step_data['time']}"
            if "distance" in step_data:
                step_info += f" | {step_data['distance']}"
                
            # 添加其他細節
            if step_data["details"]:
                step_info += " | " + " | ".join(step_data["details"])
                
            response += f"{step_info}\n"
        
        response += f"\n🔗 Google Maps導航: {route['google_maps_url']}\n"
        response += "==================\n\n"
    
    #response += "要查看完整路線細節嗎？"
    
    return response

def format_multi_stop_response(routes):
    """
    格式化多景點路線的輸出
    
    Args:
        routes (list): 包含路線信息的列表
    
    Returns:
        str: 格式化後的回應
    """
    if not routes:
        return "抱歉，無法獲取多景點路線信息。"
    
    response = "📍 多景點最佳化路線\n"
    response += "==================\n\n"
    
    for route in routes:
        response += f"🚗 路線: {route['summary']}\n"
        response += f"⏱️ 總時間: {route['total_duration']}\n"
        response += f"📏 總距離: {route['total_distance']}\n"
        response += f"🕒 預計到達時間: {route['arrival_time']}\n\n"
        
        response += "🏞️ 最佳景點順序:\n"
        for i, attraction in enumerate(route['optimized_attractions'], 1):
            response += f"  {i}. {attraction}\n"
        
        response += "\n📝 行程順序:\n"
        for i, seq in enumerate(route['route_sequence'], 1):
            response += f"  {i}. {seq}\n"
        
        response += "\n📝 簡化路線說明:\n"
        response += f"{route['simplified_route']}\n\n"
        
        response += f"🔗 Google Maps導航: {route['google_maps_url']}\n"
        response += "==================\n\n"
    
    #response += "這是根據您提供的景點優化後的最佳行程路線。需要調整嗎？"
    
    return response