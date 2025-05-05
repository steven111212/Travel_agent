import urllib.parse
import re
from datetime import datetime, timedelta
import googlemaps
import json
import sys
import os
import litellm
# 添加專案根目錄到Python路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import LLM_BASE_URL, API_TYPE, MODEL, GOOGLE_MAPS_API_KEY, CITY_MAP_JSON_PATH

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

class RouteService:
    def __init__(self):
        """初始化旅遊路線規劃器"""
        self.gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
        self.json_path = CITY_MAP_JSON_PATH


    def create_prompt(self, detail_route):
        """生成用於LLM的prompt"""
        prompt = f"""將以下詳細的導航指示簡化成極度精簡的路線概述。用戶只需要知道最關鍵的幾個路段和方向變化。

你的回應必須：
1. 限制在不超過 5 個主要路段/轉向點
2. 只提及主要高速公路和重要道路
3. 完全省略小距離和細節性指示
4. 以單一短段落呈現（最多 3-4 句話）

原始詳細路線：
{detail_route}

回應應該像是朋友間簡單描述路線的方式，不要使用列表或編號。
"""
        return prompt
    
    def get_location_address(self, location):

        with open(self.json_path, "r", encoding="utf-8") as f:
            city_map = json.load(f)
        """獲取位置的完整地址"""
        try:
            
            if location in city_map:
                location = f"{city_map[location]}政府"

            places_result = self.gmaps.places(location, language='zh-TW')
            if places_result.get('results'):
                place = places_result['results'][0]
                address = place.get('formatted_address', '無地址資訊')
            else:
                address = '無地址資訊'
            return address
        except Exception as e:
            print(f"獲取地址時出錯: {str(e)}")
            return location  # 如果出錯，返回原始位置字符串

    def create_google_maps_url(self, origin, destination, mode, waypoints=None):
        """生成Google Maps導航URL"""
        origin_encoded = urllib.parse.quote(origin)
        destination_encoded = urllib.parse.quote(destination)
        base_url = "https://www.google.com/maps/dir/?api=1"
        url = f"{base_url}&origin={origin_encoded}&destination={destination_encoded}&travelmode={mode}"
        
        if waypoints:
            waypoints = [urllib.parse.quote(waypoint) for waypoint in waypoints]
            waypoints_str = "|".join(waypoints)
            url += f"&waypoints="
            url += waypoints_str
        
        return url
    
    def get_driving_routes(self, origin, destination, language="zh-TW", alternatives=True):
        """獲取駕車路線"""
        try:
            # 準備請求參數
            origin_address = self.get_location_address(origin)
            destination_address = self.get_location_address(destination)
            
            params = {
                'origin': origin_address,
                'destination': destination_address,
                'mode': 'driving',
                'language': language,
                'alternatives': alternatives,
                'departure_time': datetime.now()
            }

            # URL編碼
            google_maps_base_url = self.create_google_maps_url(origin_address, destination_address, params['mode'])
            
            # 獲取路線
            routes = self.gmaps.directions(**params)
            results = []
            
            for i, route in enumerate(routes, 1):
                if i==2:
                    break
                # 獲取路線概要
                summary = route.get('summary', '無摘要')
                legs = route.get('legs', [])
                
                if not legs:
                    continue
                    
                leg = legs[0]
                distance = leg.get('distance', {}).get('text', '未知距離')
                duration = leg.get('duration', {}).get('text', '未知時間')

                # 提取該路線的主要路段以添加到URL
                waypoints = []
                for step in leg.get('steps', []):
                    if 'html_instructions' in step and step.get('distance', {}).get('value', 0) > 500:  # 只添加距離超過500米的主要路段
                        end_location = step.get('end_location', {})
                        if end_location:
                            lat = end_location.get('lat')
                            lng = end_location.get('lng')
                            if lat and lng:
                                waypoints.append(f"{lat},{lng}")
                
                # 根據這條路線創建特定的導航URL
                route_specific_url = google_maps_base_url
                if waypoints and len(waypoints) <= 10:  # Google Maps URL最多支持10個waypoints
                    route_specific_url = google_maps_base_url + f"&waypoints={urllib.parse.quote('|'.join(waypoints[:10]))}"
                
                detail_route = ""
                detail_route += f"路線 {i}: {summary}\n"
                detail_route += f"距離: {distance}\n"
                detail_route += f"預計時間: {duration}\n"
                
                # 顯示到達時間
                if 'duration_in_traffic' in leg:
                    arrival_time = datetime.now() + timedelta(seconds=leg['duration_in_traffic']['value'])
                else:
                    arrival_time = datetime.now() + timedelta(seconds=leg['duration']['value'])
                    
                detail_route += f"預計到達時間: {arrival_time.strftime('%H:%M:%S')}\n"
                
                # 添加詳細步驟
                for j, step in enumerate(leg.get('steps', []), 1):
                    instruction = step.get('html_instructions', '').replace('<b>', '').replace('</b>', '').replace('<div>', ', ').replace('</div>', '').replace('<div style="font-size:0.9em">', '')
                    step_distance = step.get('distance', {}).get('text', '未知距離')
                    detail_route += f"{j}. {instruction} ({step_distance})\n"
                
                # 使用LLM生成簡化路線
                # try:
                #     prompt = self.create_prompt(detail_route)
                #     messages = [{"role": "system", "content": prompt}]

                #     response = transportation_llm_api(messages=messages, max_tokens=500, temperature=0.2)
                #     simplified_route = response
                    
                # except Exception as e:
                #     print(f"生成簡化路線時出錯: {str(e)}")
                #     simplified_route = "請沿著主要道路前往目的地。詳細路線請參考Google Maps導航。"
                
                results.append({
                    'origin': origin+"("+origin_address+")",
                    'destination': destination+"("+destination_address+")",
                    'route_number': i,
                    'summary': summary,
                    'distance': distance,
                    'duration': duration,
                    'arrival_time': arrival_time.strftime('%H:%M:%S'),
                    'detail_route': detail_route,
                    #'simplified_route': simplified_route,
                    'google_maps_url': route_specific_url
                })
                
            return results
        except Exception as e:
            print(f"獲取駕車路線時出錯: {str(e)}")
            return []
    
    def get_transit_routes(self, origin, destination, language="zh-TW", alternatives=True, max_routes=1):
        """獲取公共交通路線"""
        try:
            # 準備請求參數
            origin_address = self.get_location_address(origin)
            destination_address = self.get_location_address(destination)
            
            params = {
                'origin': origin_address,
                'destination': destination_address,
                'mode': 'transit',
                'language': language,
                'alternatives': alternatives,
                'departure_time': datetime.now()
            }
            
            # URL
            google_maps_base_url = self.create_google_maps_url(origin_address, destination_address, params['mode'])
            
            # 獲取路線
            routes = self.gmaps.directions(**params)
            sorted_routes = sorted(routes, key=lambda x: x['legs'][0]['duration']['value'])
            results = []
            
            for i, route in enumerate(sorted_routes[:max_routes], 1):
                leg = route['legs'][0]
                distance = leg.get('distance', {}).get('text', '未知距離')
                duration = leg.get('duration', {}).get('text', '未知時間')
                
                # 根據這條路線創建特定的導航URL
                route_specific_url = google_maps_base_url
                
                detail_route = ""
                detail_route += f"路線 {i}\n"
                detail_route += f"距離: {distance}\n"
                detail_route += f"預計時間約: {duration}\n"
                
                # 顯示出發和到達時間
                departure_time = leg.get('departure_time', {}).get('text', '未指定')
                arrival_time = leg.get('arrival_time', {}).get('text', '未指定')
                detail_route += f"出發時間: {departure_time}\n"
                detail_route += f"預計到達時間: {arrival_time}"
                
                step_counter = 1
                
                for j, step in enumerate(leg.get('steps', []), 1):
                    # 步驟的基本資訊
                    is_walking = step.get('travel_mode') == 'WALKING'
                    step_duration_text = step['duration']['text']
                    # 從時間文字中提取數字
                    duration_number = int(re.search(r'(\d+)', step_duration_text).group(1))
                    
                    # 如果是步行且時間小於等於3分鐘，則跳過這個步驟
                    if is_walking and duration_number <= 3:
                        continue

                    # 步驟的基本資訊
                    detail_route += f"\n\n步驟 {step_counter}:"
                    step_counter += 1
                    instruction = step['html_instructions'].replace('<b>', '').replace('</b>', '').replace('<div style="font-size:0.9em">', ' - ').replace('</div>', '')
                    step_duration = step['duration']['text']
                    step_distance = step['distance']['text']
                    
                    detail_route += f"\n{instruction}"
                    detail_route += f"\n時間: {step_duration}"
                    detail_route += f"\n距離: {step_distance}"
                    
                    if step.get('travel_mode') == 'TRANSIT':
                        transit_details = step['transit_details']
                        departure_stop = transit_details['departure_stop']['name']
                        arrival_stop = transit_details['arrival_stop']['name']
                        line_name = transit_details['line'].get('name', transit_details['line'].get('short_name', '未知路線'))
                        vehicle_type = transit_details['line']['vehicle']['name']
                        
                        detail_route += f"\n交通方式: {vehicle_type}"
                        detail_route += f"\n路線: {line_name}"
                        detail_route += f"\n上車站點: {departure_stop}"
                        detail_route += f"\n下車站點: {arrival_stop}"
                        
                        # 如果有車輛號碼
                        if 'short_name' in transit_details['line']:
                            detail_route += f"\n車號: {transit_details['line']['short_name']}"
                
                results.append({
                    'route_number': i,
                    'distance': distance,
                    'duration': duration,
                    'departure_time': departure_time,
                    'arrival_time': arrival_time,
                    'detail_route': detail_route,
                    'google_maps_url': route_specific_url
                })
                
            return results
        except Exception as e:
            print(f"獲取公共交通路線時出錯: {str(e)}")
            return []
    
    def get_optimized_multi_stop_route(self, origin, destination, attractions, language="zh-TW", alternatives=True):
        """獲取多景點最佳化路線"""
        try:
            origin_address = self.get_location_address(origin)
            destination_address = self.get_location_address(destination)
            attractions_address = [self.get_location_address(attraction) for attraction in attractions]

            # 準備請求參數 - 加入waypoints並要求最佳化
            params = {
                'origin': origin_address,
                'destination': destination_address,
                'waypoints': attractions_address,  # 加入所有景點作為途經點
                'optimize_waypoints': True,  # 要求API最佳化途經點順序
                'mode': 'driving',
                'language': language,
                'alternatives': alternatives,  # 獲取多條可能路線
                'departure_time': datetime.now()
            }

            # 獲取路線
            routes = self.gmaps.directions(**params)
            results = []
            
            for i, route in enumerate(routes, 1):
                # 獲取路線概要
                summary = route.get('summary', '無摘要')
                legs = route.get('legs', [])

                if not legs:
                    continue

                # 獲取最佳化後的途經點順序
                waypoint_order = route.get('waypoint_order', [])
                optimized_attractions = [attractions[idx] for idx in waypoint_order]
                full_route = [origin] + optimized_attractions + [destination]
                route_sequence = []
                for j in range(len(full_route) - 1):
                    route_sequence.append(f"{full_route[j]} → {full_route[j+1]}")
                
                # 處理每段路線
                detail_route = f"路線 {i}: {summary}\n最佳化景點順序:\n"
                for seq in route_sequence:
                    detail_route += f"  {seq}\n"
                    
                total_distance = 0
                total_duration = 0
                
                for leg_index, leg in enumerate(legs):
                    distance = leg.get('distance', {}).get('text', '未知距離')
                    duration = leg.get('duration', {}).get('text', '未知時間')
                    start_address = leg.get('start_address', '未知起點')
                    end_address = leg.get('end_address', '未知終點')
                    
                    # 累計總距離和時間
                    total_distance += leg.get('distance', {}).get('value', 0)
                    total_duration += leg.get('duration', {}).get('value', 0)
                    
                    detail_route += f"\n從 {start_address} 到 {end_address}\n"
                    detail_route += f"距離: {distance}\n"
                    detail_route += f"預計時間: {duration}\n"
                    
                    # 顯示詳細導航步驟
                    for j, step in enumerate(leg.get('steps', []), 1):
                        instruction = step.get('html_instructions', '').replace('<b>', '').replace('</b>', '').replace('<div>', ', ').replace('</div>', '').replace('<div style="font-size:0.9em">', '')
                        step_distance = step.get('distance', {}).get('text', '未知距離')
                        detail_route += f"{j}. {instruction} ({step_distance})\n"
                
                # 計算總體資訊
                total_distance_text = f"{total_distance/1000:.1f} 公里" if total_distance > 0 else "未知總距離"
                total_hours = total_duration // 3600
                total_minutes = (total_duration % 3600) // 60
                total_duration_text = f"{total_hours}小時{total_minutes}分鐘" if total_duration > 0 else "未知總時間"
                
                # 顯示到達時間
                arrival_time = datetime.now() + timedelta(seconds=total_duration)
                
                detail_route += f"\n總距離: {total_distance_text}\n"
                detail_route += f"總時間: {total_duration_text}\n"
                detail_route += f"預計到達時間: {arrival_time.strftime('%H:%M:%S')}\n"
                
                # 使用LLM生成簡化路線描述
                # try:
                #     prompt = self.create_prompt(detail_route)
                #     messages = [{"role": "system", "content": prompt}]
                    
                #     simplified_route = transportation_llm_api(messages=messages, max_tokens=500, temperature=0.2)
                # except Exception as e:
                #     print(f"生成簡化路線時出錯: {str(e)}")
                #     simplified_route = "請依序訪問所有景點。詳細路線請參考Google Maps導航。"
                
                # 生成最終的Google Maps URL，包含最佳化的途經點順序
                optimized_url = self.create_google_maps_url(
                    origin, 
                    destination, 
                    params['mode'], 
                    optimized_attractions
                )

                results.append({
                    'route_number': i,
                    'summary': summary,
                    'optimized_attractions': optimized_attractions,
                    'route_sequence': route_sequence,
                    'total_distance': total_distance_text,
                    'total_duration': total_duration_text,
                    'arrival_time': arrival_time.strftime('%H:%M:%S'),
                    'detail_route': detail_route,
                    #'simplified_route': simplified_route,
                    'google_maps_url': optimized_url
                })
                
            return results
        except Exception as e:
            print(f"獲取多景點路線時出錯: {str(e)}")
            return []