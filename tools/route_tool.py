import sys
import os
import re
import json
from typing import Dict, List, Any, Optional, Union, Literal, ClassVar
from langchain.tools import BaseTool

# 將專案根目錄添加到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.route_service import RouteService
from config import LLM_BASE_URL, API_TYPE, MODEL, LLM_API_KEY
import litellm

class RouteTool(BaseTool):
    """路線規劃工具"""
    
    name: ClassVar[str] = "route_tool"
    description: ClassVar[str] = """這個工具可以查詢從一個地點到另一個地點的路線。
適用場景:
- 用戶想知道從A點到B點的最佳路線
- 用戶想知道如何使用大眾運輸工具前往某地
- 用戶需要多景點的最佳化路線規劃

輸入格式:
直接傳入用戶的查詢文字，例如「從台北車站到台中高鐵站怎麼去？」「從高雄到墾丁的路線」

輸出內容:
將返回路線資訊，包括距離、時間、簡化路線說明和 Google Maps 連結等"""

    def __init__(self):
        """初始化旅遊路線工具"""
        super().__init__()
        self._route_service = RouteService()
    
    def _run(self, query_input: str, history_messages: list) -> str:
        """執行路線查詢"""
        try:
            # 使用 LLM API 獲取結構化的路線資訊
            route_info = self._llm_api(query_input, history_messages)

            if route_info['mode'] == 'driving':
                # 如果交通方式是開車，並且有沿途景點，則獲取路線資訊
                if route_info['attractions']:
                    results = self._route_service.get_optimized_multi_stop_route(route_info['origin'], route_info['destination'], route_info['attractions'])
                    response = self._format_multi_stop_response(results)
                else:
                    results = self._route_service.get_driving_routes(route_info['origin'], route_info['destination'])
                    response = self._format_driving_response(results)
            elif route_info['mode'] == 'transit':
                # 如果交通方式是搭乘大眾運輸，則獲取路線資訊
                results = self._route_service.get_transit_routes(origin=route_info['origin'], destination=route_info['destination'])
                response = self._format_transit_response(results)
            
            return response
        except Exception as e:
            return f"路線查詢時發生錯誤: {str(e)}"

    def _clean_llm_response(self, response_text):
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
            # 如果無法匹配完整的 JSON，嘗試手動解析
            # 這是一個簡單的回退方案，可能不適用於所有情況
            try:
                # 使用基本的启发式方法解析
                origin_match = re.search(r'"origin"\s*:\s*"([^"]+)"', response_text)
                destination_match = re.search(r'"destination"\s*:\s*"([^"]+)"', response_text)
                mode_match = re.search(r'"mode"\s*:\s*"([^"]+)"', response_text)
                
                # 至少要能找到起點和終點
                if origin_match and destination_match:
                    result = {
                        "origin": origin_match.group(1),
                        "destination": destination_match.group(1),
                        "mode": mode_match.group(1) if mode_match else "driving",
                        "attractions": []
                    }
                    return json.dumps(result)
            except:
                pass
                
            # 如果還是失敗，創建一個默認的回應
            # 嘗試從原始查詢中提取起點和終點
            try:
                parts = response_text.split("到")
                if len(parts) >= 2:
                    origin = parts[0].split("從")[-1].strip()
                    destination = parts[1].split("的")[0].strip()
                    result = {
                        "origin": origin,
                        "destination": destination,
                        "mode": "driving",
                        "attractions": []
                    }
                    return json.dumps(result)
            except:
                pass
                
            # 如果所有嘗試都失敗，返回錯誤
            raise ValueError(f"無法從回應中提取 JSON: {response_text}")

    def _create_prompt(self) -> str:
        prompt = f"""您的任務是識別用戶旅遊查詢中的關鍵資訊，並將其轉換為結構化的JSON格式。

輸入分析要求
分析用戶的輸入查詢和歷史對話，識別以下關鍵資訊：

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
"""
        return prompt

    def _llm_api(self, query, history_messages):
        prompt = self._create_prompt()
        messages = history_messages[:-1] + [{"role": "system", "content": prompt}, {"role":"user", "content":query}]
        #print(messages)
        try:
            response = litellm.completion(
                api_key=LLM_API_KEY,
                api_base=LLM_BASE_URL,
                model=f"{API_TYPE}/{MODEL}",
                messages=messages,
                temperature=0.2, 
                max_tokens=300
            )
            response_text = response.choices[0].message.content
            cleaned_response = self._clean_llm_response(response_text)
            print(cleaned_response)
            return json.loads(cleaned_response)
        except Exception as e:
            print(f"LLM API 錯誤: {str(e)}")
            # 提供一個合理的默認值，嘗試從原始查詢中提取
            try:
                parts = query.split("到")
                if len(parts) >= 2:
                    origin = parts[0].split("從")[-1].strip()
                    destination = parts[1].split("的")[0].strip()
                    return {
                        "origin": origin,
                        "destination": destination,
                        "mode": "driving" if "開車" in query or "駕車" in query else 
                               "transit" if any(k in query for k in ["公車", "捷運", "火車", "高鐵", "客運", "公共運輸", "大眾運輸"]) else "driving",
                        "attractions": []
                    }
            except:
                pass
                
            # 如果無法提取，返回通用值
            return {
                "origin": "未知出發地",
                "destination": "未知目的地",
                "mode": "driving",
                "attractions": []
            }

    def _format_driving_response(self, routes):
        """
        格式化駕車路線的輸出
        
        Args:
            routes (list): 包含路線信息的列表
        
        Returns:
            str: 格式化後的回應
        """
        if not routes:
            return "抱歉，無法獲取駕車路線信息。請確認您提供的地點是否正確，或嘗試使用更具體的地址。"
        
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
            
            response += "📝 路線說明:\n"
            # response += f"{route['simplified_route']}\n\n"
            response += f"{route['detail_route']}\n\n"
            
            response += f"🔗 Google Maps導航: {route['google_maps_url']}\n"
            response += "==================\n\n"
        
        return response

    def _format_transit_response(self, routes):
        """
        格式化大眾運輸路線的輸出
        
        Args:
            routes (list): 包含路線信息的列表
        
        Returns:
            str: 格式化後的回應
        """
        if not routes:
            return "抱歉，無法獲取大眾運輸路線信息。請確認您提供的地點是否有大眾運輸服務，或嘗試使用更具體的地址。"
        
        response = "📍 大眾運輸路線建議\n"
        response += "==================\n\n"
        
        for route in routes:
            response += f"🚆 路線 {route['route_number']}\n"
            response += f"⏱️ 預估時間: {route['duration']}\n"
            response += f"📏 距離: {route['distance']}\n"
            # response += f"🕒 出發時間: {route['departure_time']}\n"
            # response += f"🕒 預計到達時間: {route['arrival_time']}\n\n"
            
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
        
        return response

    def _format_multi_stop_response(self, routes):
        """
        格式化多景點路線的輸出
        
        Args:
            routes (list): 包含路線信息的列表
        
        Returns:
            str: 格式化後的回應
        """
        if not routes:
            return "抱歉，無法獲取多景點路線信息。請確認您提供的地點是否正確，或嘗試使用更具體的地址。"
        
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
            #response += f"{route['simplified_route']}\n\n"
            response += f"{route['detail_route']}\n\n"
            response += f"🔗 Google Maps導航: {route['google_maps_url']}\n"
            response += "==================\n\n"
        
        return response


# 如果直接運行此檔案，則作為示範
if __name__ == "__main__":
    tool = RouteTool()
    
    # 測試路線查詢
    # test_queries = [
    #     "從台北車站到台中火車站怎麼去？",
    #     "從高雄駁二藝術特區到墾丁，順便經過高雄夢時代",
    #     "搭乘大眾運輸從台北101到淡水老街",
    #     "我想從台北101開車到宜蘭，途經南港、汐止和基隆，有沒有最佳路線建議？"
    # ]
    # test_queries = ['我想從台中開車到台北',"我想從台北101開車到宜蘭", "我想從高雄到日月潭"]
    test_queries = ['木柵到深坑']
    for query in test_queries:
        print(f"查詢: {query}")
        result = tool._run(query)
        print(result)
        print("="*80)