import sys
import os
import json
import re
from typing import Dict, List, Any, Optional, Union, Literal, ClassVar
import litellm
from datetime import datetime
import googlemaps
# 將專案根目錄添加到 Python 路徑
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.highway_service import HighwayService
from services.route_service import RouteService
from langchain.tools import BaseTool
from config import LLM_BASE_URL, API_TYPE, MODEL, LLM_API_KEY, GOOGLE_MAPS_API_KEY


class HighwayTool(BaseTool):
    """高速公路交通資訊工具類"""
    
    name: ClassVar[str] = "highway_tool"
    description: ClassVar[str] = """這個工具可以查詢台灣高速公路的即時交通狀況。
適用場景:
- 用戶想要了解特定高速公路路段的壅塞情況
- 用戶想要規劃旅途，需要知道沿途國道的交通狀況
- 用戶想要避開壅塞的路段

輸入格式:
直接傳入用戶的查詢文字，例如「國道一號現在壅塞嗎？」「從台北到高雄的國道路況如何？」「國道3號南下台中路段塞車嗎？」

輸出內容:
將返回高速公路路段的交通資訊，包括平均時速、壅塞程度、行駛方向等"""
    
    def __init__(self):
        """初始化高速公路工具"""
        super().__init__()
        self._highway_service = HighwayService()
        self._route_service = RouteService()
        
    def _run(self, query_input: str, history_messages : list) -> str:
        """
        執行高速公路交通資訊查詢
        
        參數:
            query_input (str): 用戶查詢輸入
                
        返回:
            str: 格式化的高速公路交通資訊回應
        """
        # 1. 解析用戶查詢
        query_info = self._llm_api(query_input, history_messages)
        
        # 2. 使用模糊匹配機制處理高速公路名稱
        query_info = self._resolve_highway_names(query_info)
        
        print(query_info)  # 用於調試
        
        processed_data = self._highway_service.process_highway_data()
        highways_data = processed_data.get('highways', {})

        if query_info['origin'] and query_info['destination']:
            return self._process_orgin_destination_query(query_input, query_info, highways_data)
        elif query_info['destination']:
            return self._process_specific_region_query(query_input, query_info, highways_data)
        elif query_info['highway']:
            return self._process_general_query(query_info, highways_data)
    
    def _process_specific_region_query(self, query, query_info, highways_data: Dict[str, List]) -> str:

        region_highway_map = {
            "台北": ["國道1號", "國道3號", "國道5號", "國3甲", "汐五高架", "台2己", "南港連絡道"],
            "新北": ["國道1號", "國道3號", "國道5號", "汐五高架"],
            "基隆": ["國道1號", "國道3號", "台2己"],
            "桃園": ["國道1號", "國道2號", "國道3號", "汐五高架"],
            "新竹": ["國道1號", "國道3號"],
            "苗栗": ["國道1號", "國道3號"],
            "台中": ["國道1號", "國道3號", "國道4號"],
            "彰化": ["國道1號", "國道3號", "快速公路76號"],
            "南投": ["國道3號", "國道6號"],
            "雲林": ["國道1號", "國道3號"],
            "嘉義": ["國道1號", "國道3號"],
            "台南": ["國道1號", "國道3號", "國道8號"],
            "高雄": ["國道1號", "國道3號", "國道10號", "快速公路88號"],
            "屏東": ["國道3號", "快速公路88號"],
            "宜蘭": ["國道5號"]
        }

        try:
        
            gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
            places_result = gmaps.places(query_info['destination'], language='zh-TW')
            if not places_result.get('results'):
                return f"抱歉，無法找到「{query_info['destination']}」的位置資訊。請提供更明確的地點名稱。"
                
            place = places_result['results'][0]
            address = place.get('formatted_address', '無地址資訊')

            highway_list_data = {}

            for region, highways in region_highway_map.items():
                if region in address:
                    if isinstance(query_info['highway'], list):
                        highways += query_info['highway']
                        highways = list(set(highways))
                        highway_list_data = {key: highways_data[key] for key in highways if key in highways_data}
                    else:
                        highways += [query_info['highway']]
                        highways = list(set(highways))
                        highway_list_data = {key: highways_data[key] for key in highways if key in highways_data}
                    break

            if highway_list_data:
                highway_status = self._analyze_traffic_congestion(highway_list_data, display_congestion_degrees = ['2', '3', '4', '5'])
                prompt = f"""你是一個專業的交通路線助手，負責分析行車路線並提供相關的國道交通狀況。根據以下變數提供用戶所需資訊:
                用戶查詢問題：{query}
                用戶查詢的地區地址: {address}
                國道目前的交通狀況: {highway_status}

    注意：上述「國道壅塞路段資訊」僅列出目前壅塞和嚴重壅塞的路段，未列出的路段表示交通非常順暢。

    重要限制：僅回應與交通和道路狀況相關的資訊，禁止給任何建議，禁止回答國道路況以外的問題，也不要說你無法提供或是建議。

    分析用戶查詢的位置，推測用戶可能使用的國道路段。
    接著，從國道目前的交通狀況中只篩選出與用戶所查尋地址相關的國道路段資訊：
    1. 根據地址，推測用戶可能會經過的國道交流道範圍
    2. 只提供這些交流道之間的路段狀況
    3. 特別標記出標示為「壅塞」或「嚴重壅塞」的路段
    4. 重點說明路線中可能遇到的交通壅塞路段(僅限用戶可能會經過的路段)
    5. 若路線上的國道都很順暢，則告知用戶該路線目前交通順暢

    """
                messages = [{"role": "system", "content": prompt}]
                response = litellm.completion(
                api_key=LLM_API_KEY,
                api_base=LLM_BASE_URL,
                model=f"{API_TYPE}/{MODEL}",
                messages=messages,
                temperature=0.7
            )
                response_text = response.choices[0].message.content
                return response_text
                
            else:
                return "目前沒有相關的高速公路路況資訊。"
        except Exception as e:
            print(f"處理地區查詢時出錯: {str(e)}")
            return f"處理查詢時發生錯誤，請稍後再試或提供更明確的查詢條件。"

    def _process_orgin_destination_query(self, query, query_info, highways_data: Dict[str, List]) -> str:

        results = self._route_service.get_driving_routes(query_info['origin'], query_info['destination'])
        if not results:
            return f"無法找到從 {query_info['origin']} 到 {query_info['destination']} 的路線信息。請提供更具體的地點名稱。"
        route = results[0]
        # simplified_route = route['simplified_route']
        detail_route = route['detail_route']

        highway_list = self._extract_matches(route['summary'])
        highway_list_data = {key: highways_data[key] for key in highway_list if key in highways_data}
        if highway_list_data:
            highway_status = self._analyze_traffic_congestion(highway_list_data, display_congestion_degrees = ['2', '3', '4', '5'])
            prompt = f"""你是一個專業的交通路線助手，負責分析行車路線並提供相關的國道交通狀況。根據以下變數提供用戶所需資訊:
            用戶查詢問題：{query}
            用戶的出發地: {query_info['origin']}
            用戶的目的地: {query_info['destination']}
            行車路線描述: {detail_route}
            國道目前的交通狀況: {highway_status}

注意：上述「國道壅塞路段資訊」僅列出目前壅塞和嚴重壅塞的路段，未列出的路段表示交通非常順暢。

重要限制：僅回應與交通和道路狀況相關的資訊，禁止給任何建議，禁止回答國道路況以外的問題，也不要說你無法提供或是建議。

首先，分析用戶的出發地和目的地位置，確定他們將使用的國道路段和行駛方向（北向或南向）。

接著，從國道目前的交通狀況中只篩選出與用戶實際路線相關的國道路段資訊：
1. 根據出發地和目的地的地理位置，確定用戶實際會經過的國道交流道範圍
2. 只提供這些交流道之間的路段狀況
3. 特別標記出標示為「壅塞」或「嚴重壅塞」的路段

例如：從台中到台南的路線應只考慮國道1號南向從台中到台南之間的交流道路段狀況。

以友善且資訊豐富的方式回應用戶：
1. 確認起點和終點，並簡述整體路線
2. 重點說明路線中可能遇到的交通壅塞路段(僅限用戶實際會經過的路段)
3. 若路線上的國道都很順暢，則告知用戶該路線目前交通順暢
"""
            messages = [{"role": "system", "content": prompt}]
            response = litellm.completion(
            api_key=LLM_API_KEY,
            api_base=LLM_BASE_URL,
            model=f"{API_TYPE}/{MODEL}",
            messages=messages,
            temperature=0.7
        )
            response_text = response.choices[0].message.content
            return response_text
            
        else:
            return "目前沒有相關的高速公路路況資訊。"

        

    def _process_general_query(self, query_info, highways_data: Dict[str, List]) -> str:
        """處理一般性國道查詢"""
        specific_highway_data = {}
    
        if isinstance(query_info['highway'], list):
            # 處理多條高速公路
            for highway in query_info['highway']:
                if highway in highways_data:
                    specific_highway_data[highway] = highways_data[highway]
        else:
            # 處理單條高速公路
            highway = query_info['highway']
            if highway in highways_data:
                specific_highway_data[highway] = highways_data[highway]
        
        if not specific_highway_data:
            return f"抱歉，找不到「{query_info['highway']}」的交通資訊。請確認高速公路名稱是否正確。"
        
        result = self._analyze_traffic_congestion(specific_highway_data)
        return result


    def _llm_api(self, query, history_messages):
        """使用LLM API解析用戶查詢，增強錯誤處理"""
        try:
            prompt = self._create_prompt()
            #print(history_messages)
            messages = history_messages[:-1] + [{"role": "system", "content": prompt}, {"role":"user", "content":query}]
            response = litellm.completion(
                api_key=LLM_API_KEY,
                api_base=LLM_BASE_URL,
                model=f"{API_TYPE}/{MODEL}",
                messages=messages,
                temperature=0.2
            )
            response_text = response.choices[0].message.content
            
            try:
                cleaned_response = self._clean_llm_response(response_text)
                query_info = json.loads(cleaned_response)
                
                # 確保所有必要欄位都存在
                if 'highway' not in query_info or query_info['highway'] is None:
                    query_info['highway'] = "國道1號"  # 預設值
                if 'origin' not in query_info:
                    query_info['origin'] = None
                if 'destination' not in query_info:
                    query_info['destination'] = None
                    
                return query_info
                
            except (ValueError, json.JSONDecodeError) as e:
                print(f"解析 LLM 回應時出錯: {str(e)}")
                # 提供合理的默認值
                return {
                    "highway": "國道1號",
                    "origin": None,
                    "destination": None
                }
        except Exception as e:
            print(f"LLM API 調用出錯: {str(e)}")
            # 最簡單的降級處理
            return {
                "highway": "國道1號",
                "origin": None,
                "destination": None
            }

    def _create_prompt(self) -> str:
        """
        創建 LLM 解析用的提示
        
        參數:
            query (str): 用戶查詢文字
            
        返回:
            str: LLM 提示
        """
        prompt = f"""您是一位專業的交通資訊分析助手，負責解析用戶的高速公路路況查詢請求。請分析用戶的查詢及歷史對話紀錄，並提取關鍵資訊，以JSON格式回傳。

您需要識別以下資訊：
1. highway (國道名稱): 例如國道1號、國道3號等, 如果用戶提到多條國道，請將它們以列表形式返回
2. origin (出發地): 用戶提到的出發地點
3. destination (目的地): 用戶提到的目的地點

如果用戶詢問國道路況但沒有提供具體的國道名稱又沒提供地點，一律當作詢問國道1號。

可能的國道名稱包括：
['國道1號', '汐五高架', '國道2號', '國2甲', '國道3號', '國3甲', '台2己', '南港連絡道', '國道4號', '國道5號', '國道6號', '國道8號', '國道10號', '快速公路76號', '快速公路88號']

請注意：
- 如果某項資訊未在查詢中提及，請將該欄位設為null。


請以以下JSON格式回覆：
```json
{{
  "highway": "國道X號或null",
  "origin": "出發地或null",
  "destination": "目的地或null"
}}
```
只需返回JSON，不需要任何其他解釋。"""
        return prompt
    
    # 匹配高速公路名稱
    def _resolve_highway_names(self, query_info: Dict) -> Dict:
        """將模糊的高速公路名稱轉換為標準名稱
        
        參數:
            query_info (Dict): 包含解析後查詢資訊的字典
            
        返回:
            Dict: 更新後的查詢資訊
        """
        if 'highway' not in query_info or query_info['highway'] is None:
            query_info['highway'] = "國道1號"  # 提供默認值
            return query_info
        # 定義高速公路名稱映射表
        highway_mapping = {
            # 國道1號的常見稱呼
            "中山高": "國道1號",
            "中山高速公路": "國道1號",
            "國1": "國道1號",
            "國一": "國道1號",
            "1號高速公路": "國道1號",
            "一號高速公路": "國道1號",
            "中山高速": "國道1號",
            
            # 國道3號的常見稱呼
            "福爾摩沙高速公路": "國道3號",
            "二高": "國道3號",
            "北二高": "國道3號",
            "國3": "國道3號",
            "國三": "國道3號",
            "3號高速公路": "國道3號",
            "三號高速公路": "國道3號",
            
            # 國道5號的常見稱呼
            "蔣渭水高速公路": "國道5號",
            "國5": "國道5號",
            "國五": "國道5號",
            "5號高速公路": "國道5號",
            "五號高速公路": "國道5號",
            
            # 國道2號的常見稱呼
            "機場聯絡道": "國道2號",
            "國2": "國道2號",
            "國二": "國道2號",
            "2號高速公路": "國道2號",
            "二號高速公路": "國道2號",
            
            # 國道4號的常見稱呼
            "國4": "國道4號",
            "國四": "國道4號",
            "4號高速公路": "國道4號",
            "四號高速公路": "國道4號",
            
            # 國道6號的常見稱呼
            "國6": "國道6號",
            "國六": "國道6號",
            "6號高速公路": "國道6號",
            "六號高速公路": "國道6號",
            
            # 國道8號的常見稱呼
            "國8": "國道8號",
            "國八": "國道8號",
            "8號高速公路": "國道8號",
            "八號高速公路": "國道8號",
            
            # 國道10號的常見稱呼
            "國10": "國道10號",
            "國十": "國道10號",
            "10號高速公路": "國道10號",
            "十號高速公路": "國道10號",
            
            # 其他路段常見稱呼
            "汐止高架": "汐五高架",
            "南港聯絡道": "南港連絡道",
        }
        
        # 處理單個高速公路字串情況
        if isinstance(query_info['highway'], str):
            # 如果是模糊名稱，則轉換
            if query_info['highway'] in highway_mapping:
                query_info['highway'] = highway_mapping[query_info['highway']]
            # 如果只提到"國道"或"高速公路"但沒有具體號碼，預設為國道1號
            elif query_info['highway'] in ["國道", "高速公路"]:
                query_info['highway'] = "國道1號"
        
        # 處理多個高速公路清單情況
        elif isinstance(query_info['highway'], list):
            resolved_highways = []
            for highway in query_info['highway']:
                if highway in highway_mapping:
                    resolved_highways.append(highway_mapping[highway])
                elif highway in ["國道", "高速公路"]:
                    # 如果只提到"國道"，則添加主要國道
                    resolved_highways.extend(["國道1號", "國道3號"])
                else:
                    resolved_highways.append(highway)
            query_info['highway'] = resolved_highways
        
        return query_info
    
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
            raise ValueError(f"無法從回應中提取 JSON: {response_text}")
    
    def _analyze_traffic_congestion(self, data, display_congestion_degrees = ['3', '4', '5']):
        """
        分析交通壅塞資料並生成格式化輸出
        
        參數:
        data (dict): 交通資料，格式為 {'高速公路名稱': [路段資料列表]}
        
        返回:
        str: 格式化的壅塞路段報告
        """
        # 定義壅塞程度對應的顯示
        congestion_display = {
            '1': '順暢',
            '2': '車多但順暢',
            '3': '壅塞',
            '4': '嚴重壅塞',
            '5': '嚴重壅塞'
        }

        congestion_icon = {
            '1': '✅',
            '2': '✅',
            '3': '⚠️',
            '4': '🔴',
            '5': '🔴'
        }

        # 分別存儲各方向的壅塞路段
        congestion_sections = {}

        # 處理每條高速公路
        for highway, sections in data.items():
            for section in sections:
                # 只關注壅塞的路段
                if section['congestionDegree'] in display_congestion_degrees:
                    direction = section['direction']
                    
                    # 確保方向鍵存在
                    if direction not in congestion_sections:
                        congestion_sections[direction] = []
                        
                    congestion_sections[direction].append({
                        'highway': highway,
                        'section': section['section'],
                        'from': section['from'],
                        'to': section['to'],
                        'speed': section['speed'],
                        'congestionDegree': section['congestionDegree']
                    })

        # 整理並輸出結果
        output = "國道有以下幾處壅塞路段：\n"

        # 處理南向
        if '南下' in congestion_sections and congestion_sections['南下']:
            south_sections = self._merge_consecutive_sections(congestion_sections['南下'])
            if south_sections:
                output += "南向壅塞路段:\n"
                for section in south_sections:
                    congestion = congestion_display[section['congestionDegree']]
                    icon = congestion_icon[section['congestionDegree']]
                    output += f"- {section['section']}：時速{int(section['speed'])}公里, {icon}{congestion}\n"

        # 處理北向
        if '北上' in congestion_sections and congestion_sections['北上']:
            north_sections = self._merge_consecutive_sections(congestion_sections['北上'])
            if north_sections:
                output += "北向壅塞路段:\n"
                for section in north_sections:
                    congestion = congestion_display[section['congestionDegree']]
                    icon = congestion_icon[section['congestionDegree']]
                    output += f"- {section['section']}：時速{int(section['speed'])}公里, {icon}{congestion}\n"

        # 處理無方向
        if '' in congestion_sections and congestion_sections['']:
            no_direction_sections = self._merge_consecutive_sections(congestion_sections[''])
            if no_direction_sections:
                output += "無方向壅塞路段:\n"
                for section in no_direction_sections:
                    congestion = congestion_display[section['congestionDegree']]
                    icon = congestion_icon[section['congestionDegree']]
                    output += f"- {section['section']}：時速{int(section['speed'])}公里, {icon}{congestion}\n"

        # 處理其他方向
        other_directions = [dir for dir in congestion_sections.keys() if dir not in ['南下', '北上', '']]
        for direction in other_directions:
            sections = self._merge_consecutive_sections(congestion_sections[direction])
            if sections:
                output += f"{direction}壅塞路段:\n"
                for section in sections:
                    congestion = congestion_display[section['congestionDegree']]
                    icon = congestion_icon[section['congestionDegree']]
                    output += f"- {section['section']}：時速{int(section['speed'])}公里, {icon}{congestion}\n"

        if "南向壅塞路段:" not in output and "北向壅塞路段:" not in output and "無方向壅塞路段:" not in output:
            return "目前路況良好，沒有發現壅塞路段。"

        return output

# 合併連續的相同壅塞程度路段
    def _merge_consecutive_sections(self, sections):
        if not sections:
            return []
            
        # 先按高速公路名稱排序
        sections.sort(key=lambda x: x['highway'])
        
        merged = []
        current_group = []
        
        for section in sections:
            if not current_group:
                current_group.append(section)
                continue
                
            previous = current_group[-1]
            
            # 如果是相同高速公路、壅塞程度相同且連續
            if (section['highway'] == previous['highway'] and 
                section['congestionDegree'] == previous['congestionDegree'] and
                section['from'] == previous['to']):
                # 合併到當前組
                current_group.append(section)
            else:
                # 完成當前組並開始新組
                if len(current_group) == 1:
                    merged.append(current_group[0])
                else:
                    # 合併多個連續路段
                    first = current_group[0]
                    last = current_group[-1]
                    merged.append({
                        'highway': first['highway'],
                        'section': f"{first['highway']}({first['from']}到{last['to']})",
                        'from': first['from'],
                        'to': last['to'],
                        'speed': sum([s['speed'] for s in current_group]) / len(current_group),
                        'congestionDegree': first['congestionDegree']
                    })
                current_group = [section]
        
        # 處理最後一組
        if current_group:
            if len(current_group) == 1:
                merged.append(current_group[0])
            else:
                first = current_group[0]
                last = current_group[-1]
                merged.append({
                    'highway': first['highway'],
                    'section': f"{first['highway']}({first['from']}到{last['to']})",
                    'from': first['from'],
                    'to': last['to'],
                    'speed': sum([s['speed'] for s in current_group]) / len(current_group),
                    'congestionDegree': first['congestionDegree']
                })
        
        return merged

    def _extract_matches(self, input_string):
        matches = []
        list_items = ['國道1號', '汐五高架', '國道2號', '國2甲', '國道3號', '國3甲', '台2己', 
            '南港連絡道', '國道4號', '國道5號', '國道6號', '國道8號', '國道10號', 
            '快速公路76號', '快速公路88號']
            
        for item in list_items:
            if item in input_string:
                matches.append(item)
        return matches
    

if __name__ == "__main__":
    tool = HighwayTool()
    
    # 測試模糊匹配
    test_queries = [
        "中山高現在塞車嗎？",
        "國一和國三的路況如何？",
        "台中到台南國一和國三順暢嗎",
        "二高南下台中路段壅塞嗎？",
        "機場聯絡道有沒有車多的情況？",
        "國道路況如何？",
    ]
    
    for query in test_queries:
        print(f"\n測試查詢: {query}")
        result = tool._run(query)
        print(result)