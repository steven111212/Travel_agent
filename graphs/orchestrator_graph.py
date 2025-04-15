import sys
import os
import json
import re
import litellm
from langchain_core.messages import HumanMessage, AIMessage
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

# 引入您已經創建的工具
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import HighwayTool, ParkingTool, RouteTool, WeatherTool, GeneralTool
from config import LLM_BASE_URL, API_TYPE, MODEL, LLM_API_KEY

# 定義字典部分更新策略
def assign_partial(current_dict, new_dict):
    """合併兩個字典"""
    result = current_dict.copy()  # 複製當前字典
    result.update(new_dict)  # 更新新的值
    return result

# 初始化工具
highway_tool = HighwayTool()
route_tool = RouteTool()
weather_tool = WeatherTool()
parking_tool = ParkingTool()
general_tool = GeneralTool()


# 定義狀態類型
class AgentState(TypedDict):
    """Agent 狀態定義"""
    messages: List[Dict[str, str]]  # 對話歷史
    query: str  # 用戶查詢
    tools_to_use: List[str]  # 需要使用的工具
    tool_results: Annotated[Dict[str, str], assign_partial]
    final_response: Optional[str]

# 工具調用函數也需要簡化
def call_highway_tool(state: AgentState) -> Dict[str, Any]:
    """調用高速公路工具"""
    print(f"調用高速公路工具，查詢：{state['query']}")
    result = highway_tool._run(state["query"])
    # 只返回要更新的鍵
    return {"tool_results": {"highway": result}}

def call_route_tool(state: AgentState) -> Dict[str, Any]:
    """調用路線規劃工具"""
    print(f"調用路線規劃工具，查詢：{state['query']}")
    result = route_tool._run(state["query"])
    return {"tool_results": {"route": result}}

def call_weather_tool(state: AgentState) -> Dict[str, Any]:
    """調用天氣工具"""
    print(f"調用天氣工具，查詢：{state['query']}")
    result = weather_tool._run(state["query"])
    return {"tool_results": {"weather": result}}

def call_parking_tool(state: AgentState) -> Dict[str, Any]:
    """調用停車場查詢工具"""
    print(f"調用停車場查詢工具，查詢：{state['query']}")
    result = parking_tool._run(state["query"])
    # 這裡可以根據需要添加停車場工具的邏輯
    return {"tool_results": {"parking": result}}  # 假設返回的結果

def call_general_tool(state: AgentState) -> Dict[str, Any]:
    """調用一般性旅遊查詢工具"""
    print(f"調用一般性旅遊查詢工具，查詢：{state['query']}")
    result = general_tool._run(state["query"])
    return {"tool_results": {"general": result}}  # 假設返回的結果

# 決策函數
def decide_tools(state: AgentState) -> Dict[str, Any]:
    """分析查詢，決定使用哪些工具"""
    query = state["query"]
    tools = analyze_query(query)
    print(f"決定使用的工具：{tools}")
    return {"tools_to_use": tools}

def analyze_query(query: str) -> List[str]:
    """
    分析用戶查詢，決定應該使用哪些工具
    
    參數:
        query (str): 用戶查詢
        
    返回:
        List[str]: 需要使用的工具列表
    """
    # 使用 LLM 來判斷需要使用哪些工具
    prompt = create_analysis_prompt(query)
    messages = [{"role": "system", "content": prompt}]
    
    try:
        response = litellm.completion(
            api_key=LLM_API_KEY,
            api_base=LLM_BASE_URL,
            model=f"{API_TYPE}/{MODEL}",
            messages=messages,
            temperature=0.2
        )
        response_text = response.choices[0].message.content
        
        # 解析 LLM 回應
        tools_to_use = parse_llm_analysis(response_text)
        
        # 如果沒有識別出工具，默認使用一般性旅遊查詢工具
        if not tools_to_use:
            return ["general_tool"]
            
        return tools_to_use
        
    except Exception as e:
        print(f"工具分析時出錯: {str(e)}")
        # 如果分析失敗，嘗試基於關鍵詞的簡單規則來判斷
        return fallback_tool_selection(query)

def create_analysis_prompt(query: str) -> str:
    """
    創建用於分析查詢的 LLM 提示
    
    參數:
        query (str): 用戶查詢
        
    返回:
        str: LLM 提示
    """
    prompt = f"""您是一個台灣旅遊助手的意圖分析器。請分析用戶的查詢並確定需要使用哪些工具來回答。

可用的工具有:

1. highway_tool: 提供高速公路交通狀況資訊，適用於:
   - 用戶詢問特定高速公路路段的壅塞情況
   - 用戶詢問從一地到另一地的高速公路狀況
   - 包含關鍵詞: 國道、高速公路、交流道、塞車、壅塞、路況

2. route_tool: 提供路線規劃，適用於:
   - 用戶詢問從一地到另一地的路線
   - 用戶詢問多景點的行程規劃
   - 包含關鍵詞: 怎麼去、路線、路徑、規劃

3. weather_tool: 提供天氣資訊，適用於:
   - 用戶詢問特定地點的天氣狀況
   - 用戶詢問多日的天氣預報
   - 必須包含關鍵詞: 天氣、氣溫、降雨、下雨、濕度、紫外線
   - 用戶沒提到天氣的情況下，這個工具不會被使用

4. parking_tool: 提供停車場資訊，適用於:
   - 用戶詢問特定地點的停車場資訊

請分析以下用戶查詢，判斷需要使用哪些工具來回答。多個工具可能需要同時使用。

用戶查詢: {query}

請以 JSON 格式回覆，僅包含工具名稱列表:
{{
  "tools": ["tool_name1", "tool_name2", ...]
}}
只需返回 JSON，不需要任何其他解釋。"""
    
    return prompt

def parse_llm_analysis(response_text: str) -> List[str]:
    """
    解析 LLM 回應，提取需要使用的工具列表
    
    參數:
        response_text (str): LLM 回應文本
        
    返回:
        List[str]: 工具列表
    """
    try:
        # 嘗試匹配 JSON 內容
        json_pattern = r'```json\s*({.*?})\s*```|^{.*}$'
        match = re.search(json_pattern, response_text, re.DOTALL)
        
        if match:
            json_str = match.group(1) if match.group(1) else match.group(0)
            json_str = json_str.strip()
            result = json.loads(json_str)
            return result.get("tools", [])
        
        # 如果沒有匹配到 JSON，嘗試直接解析工具名稱
        tool_pattern = r'(highway_tool|route_tool|weather_tool|parking_tool)'
        matches = re.findall(tool_pattern, response_text)
        return list(set(matches))
        
    except Exception as e:
        print(f"解析工具分析結果時出錯: {str(e)}")
        return []

def fallback_tool_selection(query: str) -> List[str]:
    """
    基於關鍵詞的簡單規則來選擇工具 (作為分析失敗時的備選方案)
    
    參數:
        query (str): 用戶查詢
        
    返回:
        List[str]: 工具列表
    """
    tools = []
    
    # 高速公路相關關鍵詞
    highway_keywords = ["國道", "高速公路", "交流道", "塞車", "壅塞", "路況", 
                       "中山高", "二高", "國1", "國3", "國5"]
    
    # 路線規劃相關關鍵詞
    route_keywords = ["怎麼去", "路線", "路徑", "規劃", "從", "到", "前往", 
                     "出發", "抵達", "距離", "時間"]
    
    # 天氣相關關鍵詞
    weather_keywords = ["天氣", "氣溫", "降雨", "濕度", "紫外線", "下雨", 
                       "晴天", "陰天", "颱風", "溫度"]
    
    # 停車場相關關鍵詞
    parking_keywords = ["停車場", "停車位", "停車", "停車資訊",]
    
    # 檢查查詢中是否包含各類關鍵詞
    query_lower = query.lower()
    
    if any(keyword in query_lower for keyword in highway_keywords):
        tools.append("highway_tool")
        
    if any(keyword in query_lower for keyword in route_keywords):
        tools.append("route_tool")
        
    if any(keyword in query_lower for keyword in weather_keywords):
        tools.append("weather_tool")

    if any(keyword in query_lower for keyword in parking_keywords):
        tools.append("parking_tool")
    
    # 如果沒有匹配任何工具，返回所有工具
    if not tools:
        return ["general_tool"]
        
    return tools

# 選擇下一步
def route_to_tools(state: AgentState) -> List[str]:
    """
    根據決策結果選擇下一步調用哪些工具
    
    參數:
        state (AgentState): 當前狀態
        
    返回:
        List[str]: 需要執行的節點列表
    """
    tools = state["tools_to_use"]
    result = []

    # 檢查是否包含特定工具
    specific_tools = False
    
    if "highway_tool" in tools:
        result.append("highway")
        specific_tools = True
    if "route_tool" in tools:
        result.append("route")
        specific_tools = True
    if "weather_tool" in tools:
        result.append("weather")
        specific_tools = True
    if "parking_tool" in tools:
        result.append("parking")
        specific_tools = True
    # 只有在沒有其他特定工具時，才使用 general_tool
    if not specific_tools and "general_tool" in tools:
        result.append("general")
    
    # 關鍵：返回一個節點列表，這些節點會被並行執行
    if result:
        return result
    
    # 如果沒有工具需要調用，直接進入合成階段
    return ["synthesize"]

# 合成結果
def synthesize_results(state: AgentState) -> Dict[str, Any]:
    """
    整合所有工具的結果
    
    參數:
        state (AgentState): 當前狀態
        
    返回:
        Dict[str, Any]: 更新後的狀態
    """
    query = state["query"]
    tool_results = state["tool_results"]
    
    # 當沒有工具結果時的處理
    if not tool_results:
        response = "抱歉，我無法處理您的查詢。請嘗試提供更具體的問題。"
        return {
            "final_response": response,
            "messages": state["messages"] + [{"role": "assistant", "content": response}]
        }
    
    # 使用 LLM 整合多個工具的回應
    integrated_response = integrate_responses(query, tool_results)
    
    # 更新狀態
    return {
        "final_response": integrated_response,
        "messages": state["messages"] + [{"role": "assistant", "content": integrated_response}]
    }

def integrate_responses(query: str, tool_responses: Dict[str, str]) -> str:
    """
    整合各工具的回應，生成最終的回應
    優化版本：直接拼接多個工具的結果，不使用 LLM 整合
    
    參數:
        query (str): 原始用戶查詢
        tool_responses (Dict[str, str]): 各工具的回應
        
    返回:
        str: 整合後的回應
    """
    # 如果只有一個工具的回應，直接返回
    if len(tool_responses) == 1:
        return list(tool_responses.values())[0]
    
    # 多個工具回應時，直接拼接而不使用 LLM
    result = "以下是您查詢的相關資訊:\n\n"
    
    # 根據工具的類型優先排序
    if "route" in tool_responses and "highway" not in tool_responses:
        result += "🗺️ 路線規劃:\n"
        result += tool_responses["route"] + "\n\n"
        
    if "weather" in tool_responses:
        result += "🌤️ 天氣資訊:\n"
        result += tool_responses["weather"] + "\n\n"

    if "highway" in tool_responses:
        result += "🛣️ 高速公路交通資訊:\n"
        result += tool_responses["highway"] + "\n\n"

    if "parking" in tool_responses:
        result += "🅿️ 停車場資訊:\n"
        result += tool_responses["parking"] + "\n\n"
    
    if "general" in tool_responses:
        result += "💬 一般旅遊建議:\n"
        result += tool_responses["general"] + "\n\n"
    
    # 簡單的總結
    if len(tool_responses) >= 2:
        result += "希望以上資訊能幫助到您！祝您旅途愉快。\n"
        
    return result

def create_integration_prompt(query: str, tool_responses: Dict[str, str]) -> str:
    """
    創建用於整合回應的 LLM 提示
    
    參數:
        query (str): 用戶查詢
        tool_responses (Dict[str, str]): 各工具的回應
        
    返回:
        str: LLM 提示
    """
    # 構建提示內容
    prompt = f"""您是一個台灣旅遊助手，負責將多個專業工具的回應整合成一個連貫、友善、有組織的回應。

用戶原始查詢:
{query}

以下是各個專業工具的回應:
"""
    if "highway" in tool_responses:
        prompt += f"""
==== 高速公路交通資訊 ====
{tool_responses["highway"]}
"""
    
    if "route" in tool_responses:
        prompt += f"""
==== 路線規劃 ====
{tool_responses["route"]}
"""
    
    if "weather" in tool_responses:
        prompt += f"""
==== 天氣資訊 ====
{tool_responses["weather"]}
"""
    
    if "parking" in tool_responses:
        prompt += f"""
==== 停車場資訊 ====
{tool_responses["parking"]}
"""    
    prompt += """
請將以上資訊整合成一個連貫的回應，避免重複資訊，並根據問題的核心需求進行優先排序，使用繁體中文回答。
回應應該:
1. 先回答用戶最關心的問題
2. 將相關資訊組織在一起
3. 提供一個簡短的總結，包含最重要的提醒或建議
4. 保持友善、專業的語氣
5. 盡量採用原本的語言風格，讓用戶感到親切

請提供整合後的完整回應:"""
    
    return prompt

# 創建 LangGraph 工作流
def create_travel_assistant_workflow():
    """創建旅遊助手工作流"""
    # 初始化 StateGraph
    workflow = StateGraph(AgentState)
    
    # 添加節點
    workflow.add_node("decide", decide_tools)
    workflow.add_node("highway", call_highway_tool)
    workflow.add_node("route", call_route_tool)
    workflow.add_node("weather", call_weather_tool)
    workflow.add_node("parking", call_parking_tool)
    workflow.add_node("general", call_general_tool)
    workflow.add_node("synthesize", synthesize_results)
    
    # 設置入口點
    workflow.set_entry_point("decide")
    
    # 添加條件邊，從 decide 到其他節點
    workflow.add_conditional_edges("decide", route_to_tools)
    
    # 所有工具節點指向 synthesize 節點
    workflow.add_edge("highway", "synthesize")
    workflow.add_edge("route", "synthesize")
    workflow.add_edge("weather", "synthesize")
    workflow.add_edge("parking", "synthesize")
    workflow.add_edge("general", "synthesize")
    workflow.add_edge("synthesize", END)
    
    # 編譯工作流
    return workflow.compile()

# 創建旅遊助手類
class TravelAssistant:
    """旅遊助手類，封裝 LangGraph 工作流"""
    
    def __init__(self):
        """初始化旅遊助手"""
        self.graph = create_travel_assistant_workflow()
    
    def process_query(self, query: str) -> str:
        """
        處理用戶查詢
        
        參數:
            query (str): 用戶查詢
            
        返回:
            str: 回應
        """
        # 初始化狀態
        initial_state = {
            "messages": [{"role": "user", "content": query}],
            "query": query,
            "tools_to_use": [],
            "tool_results": {},
            "final_response": None
        }
        
        # 執行工作流
        final_state = self.graph.invoke(initial_state)
        
        # 返回最終回應
        return final_state["final_response"]
        
    def stream_process(self, query: str):
        """
        流式處理用戶查詢，可以看到每個步驟的執行結果
        
        參數:
            query (str): 用戶查詢
            
        返回:
            generator: 每個步驟的執行結果
        """
        # 初始化狀態
        initial_state = {
            "messages": [{"role": "user", "content": query}],
            "query": query,
            "tools_to_use": [],
            "tool_results": {},
            "final_response": None
        }
        
        # 流式執行工作流
        for state in self.graph.stream(initial_state):
            yield state


# 如果直接運行此檔案，則作為示範
if __name__ == "__main__":
    # 初始化旅遊助手
    import time
    assistant = TravelAssistant()
    
    # 測試查詢
    test_queries = [
        #"我想從台北到宜蘭，國道五號的路況如何？請也順便告訴我宜蘭明天的天氣。",
        #"從台中到日月潭的路線，途中會經過哪些景點？週末那邊的天氣如何？",
        "台北車站附近哪裡可以停車",
        "我想去爬山我要注意些什麼事情?"
    ]
    
    # 測試單一查詢
    # query = "我想從台北到宜蘭，國道五號的路況如何？請也順便告訴我宜蘭明天的天氣。"
    # print(f"\n測試查詢: {query}")
    
    # 使用流式處理來查看每個步驟
    # print("\n=== 流式處理 ===")
    # for state in assistant.stream_process(query):
    #     # 打印當前狀態
    #     if "tools_to_use" in state and state["tools_to_use"]:
    #         print(f"選擇使用的工具: {state['tools_to_use']}")
    #     if "tool_results" in state and state["tool_results"]:
    #         tools_done = list(state["tool_results"].keys())
    #         if tools_done:
    #             print(f"完成的工具: {tools_done}")
    #     if "final_response" in state and state["final_response"]:
    #         print("\n最終回應:")
    #         print(state["final_response"])
    
    # 測試所有查詢
    print("\n\n=== 測試所有查詢 ===")
    for query in test_queries:
        start_time = time.time()
        print(f"\n測試查詢: {query}")
        result = assistant.process_query(query)
        print("回應:", result)
        elapsed_time = time.time() - start_time
        print(f"回應 (耗時 {elapsed_time:.2f}秒):")
        print("="*80)