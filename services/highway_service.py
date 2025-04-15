import sys
import os
import requests
import time
import random
from typing import Dict, List, Any, Optional
import sys
from datetime import datetime, timedelta
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CLIENT_ID, CLIENT_SECRET

class HighwayService:
    """高速公路交通資訊服務類"""
    
    def __init__(self):
        """
        初始化高速公路服務
        
        參數:
            client_id (str): TDX API的客戶端ID
            client_secret (str): TDX API的客戶端密鑰
        """
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.access_token = None
        self.section_data = {}
        self.traffic_data = {}
        self.processed_data = {}
        self.last_refresh_time = None
        self.cache_duration = 900  # 緩存持續時間，單位為秒（5分鐘）
        self.max_retries = 3       # 最大重試次數
        self.cache_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../data/traffic_data_cache.json")
        
        # 初始化時獲取訪問令牌
        self._get_access_token()
        
        # 嘗試從緩存加載數據
        if not self._load_cache():
            # 如果沒有可用的緩存，則獲取新數據
            self._get_highway_sections()
            self._get_live_traffic()
            self._process_highway_data()
            # 保存到緩存
            self._save_cache()
    
    def _get_access_token(self) -> None:
        """從TDX API獲取訪問令牌"""
        auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        for attempt in range(self.max_retries):
            try:
                auth_response = requests.post(auth_url, data=auth_data)
                auth_response.raise_for_status()  # 檢查HTTP錯誤
                self.access_token = auth_response.json()["access_token"]
                return
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    # 如果是速率限制錯誤且不是最後一次嘗試，等待一段時間後重試
                    wait_time = (2 ** attempt) + random.uniform(0, 1)  # 指數退避策略
                    print(f"獲取訪問令牌被限流，等待 {wait_time:.2f} 秒後重試...")
                    time.sleep(wait_time)
                else:
                    print(f"獲取訪問令牌時出錯: {str(e)}")
                    raise
            except Exception as e:
                print(f"獲取訪問令牌時出錯: {str(e)}")
                raise
    
    def _load_cache(self) -> bool:
        """
        從緩存文件加載數據
        
        返回:
            bool: 是否成功加載緩存
        """
        try:
            if os.path.exists(self.cache_file_path):
                with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # 檢查緩存是否過期
                cache_time = datetime.fromisoformat(cache_data.get('timestamp', '2000-01-01T00:00:00'))
                if datetime.now() - cache_time < timedelta(seconds=self.cache_duration):
                    # 加載數據
                    self.processed_data = cache_data
                    self.last_refresh_time = cache_time
                    print(f"成功從緩存加載數據，緩存時間: {cache_time.isoformat()}")
                    return True
                else:
                    print("緩存已過期，將獲取新數據")
            else:
                print("無可用緩存，將獲取新數據")
            return False
        except Exception as e:
            print(f"讀取緩存時出錯: {str(e)}")
            return False
    
    def _save_cache(self) -> None:
        """將數據保存到緩存文件"""
        try:
            # 只保留highways和timestamp
            cache_data = {
                'highways': self.processed_data.get('highways', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            # 確保目錄存在
            os.makedirs(os.path.dirname(self.cache_file_path), exist_ok=True)
            
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.last_refresh_time = datetime.now()
            print(f"數據已保存到緩存，時間: {self.last_refresh_time.isoformat()}")
        except Exception as e:
            print(f"保存緩存時出錯: {str(e)}")
    
    def _make_api_request(self, url: str, method: str = 'get', data: Optional[Dict] = None) -> Dict:
        """
        發送API請求，帶有重試機制
        
        參數:
            url (str): API URL
            method (str): 請求方法，默認為'get'
            data (Dict, optional): 請求數據
            
        返回:
            Dict: API響應
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        for attempt in range(self.max_retries):
            try:
                if method.lower() == 'post':
                    response = requests.post(url, headers=headers, json=data)
                else:
                    response = requests.get(url, headers=headers)
                
                response.raise_for_status()  # 檢查HTTP錯誤
                return response.json()
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    # 如果是速率限制錯誤且不是最後一次嘗試，等待一段時間後重試
                    wait_time = (2 ** attempt) + random.uniform(0, 1)  # 指數退避策略
                    print(f"API請求被限流，等待 {wait_time:.2f} 秒後重試...")
                    time.sleep(wait_time)
                elif e.response.status_code == 401 and attempt < self.max_retries - 1:
                    # 如果是授權錯誤，嘗試重新獲取訪問令牌
                    print("訪問令牌可能已過期，重新獲取...")
                    self._get_access_token()
                else:
                    print(f"API請求時出錯: {str(e)}")
                    raise
            except Exception as e:
                print(f"API請求時出錯: {str(e)}")
                raise
    
    def _get_highway_sections(self) -> None:
        """獲取高速公路路段資訊"""
        url = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Section/Freeway"
        
        try:
            data = self._make_api_request(url)
            
            # 建立路段ID到路段名稱的映射
            for section in data.get('Sections', []):
                self.section_data[section.get('SectionID')] = section.get('SectionName')
        except Exception as e:
            print(f"獲取高速公路路段資訊時出錯: {str(e)}")
            raise
    
    def _get_live_traffic(self) -> None:
        """獲取高速公路即時交通資訊"""
        url = "https://tdx.transportdata.tw/api/basic/v2/Road/Traffic/Live/Freeway"
        
        try:
            self.traffic_data = self._make_api_request(url)
        except Exception as e:
            print(f"獲取高速公路即時交通資訊時出錯: {str(e)}")
            raise
    
    def _process_highway_data(self) -> None:
        """處理從API取得的資料，組織成適合查詢的結構"""
        if not self.section_data or not self.traffic_data:
            return
        
        # 解析所有的路段資訊
        highways = {}
        
        for traffic in self.traffic_data.get('LiveTraffics', []):
            section_id = traffic.get('SectionID')
            if section_id not in self.section_data:
                continue
                
            section_name = self.section_data[section_id]
            
            # 解析路段名稱
            parts = section_name.split('(')
            if len(parts) < 2:
                continue
                
            highway = parts[0].strip()
            section_detail = parts[1].replace(')', '').strip()
            
            # 解析起點和終點
            section_parts = section_detail.split('到')
            if len(section_parts) < 2:
                continue
                
            from_point = section_parts[0].strip()
            to_point = section_parts[1].strip()
            
            # 建立路段資訊
            section_info = {
                'sectionId': section_id,
                'section': section_name,
                'from': from_point,
                'to': to_point,
                'speed': traffic.get('TravelSpeed'),
                'congestionDegree': traffic.get('CongestionLevel'),
                'direction': ''  # 預設為空字串，後續補充
            }
            
            # 加入對應的高速公路資料結構，移除sections層級
            if highway not in highways:
                highways[highway] = []
            
            highways[highway].append(section_info)
        
        # 補充方向資訊
        self._add_direction_info(highways)
        
        # 整合結果
        self.processed_data = {
            'highways': highways,
        }
    
    def refresh_data(self) -> None:
        """刷新高速公路資料"""
        # 檢查是否需要刷新數據（如果距離上次刷新時間不足5分鐘，則跳過）
        if self.last_refresh_time and datetime.now() - self.last_refresh_time < timedelta(seconds=self.cache_duration):
            print(f"數據最近已更新（{(datetime.now() - self.last_refresh_time).total_seconds():.1f}秒前），跳過刷新")
            return
            
        try:
            # 嘗試刷新訪問令牌
            self._get_access_token()
            
            # 獲取新數據
            self._get_highway_sections()
            self._get_live_traffic()
            self._process_highway_data()
            
            # 保存到緩存
            self._save_cache()
        except Exception as e:
            print(f"刷新數據時出錯: {str(e)}")
            print("將使用緩存數據（如果有）")
            self._load_cache()
    
    def fetch_highway_data(self) -> Dict:
        """
        從TDX API獲取高速公路資料的接口方法
        
        返回:
            Dict: 包含sections的字典
        """
        # 如果數據可能已過期，嘗試刷新
        if not self.last_refresh_time or datetime.now() - self.last_refresh_time > timedelta(seconds=self.cache_duration):
            try:
                print("數據可能已過期，嘗試刷新...")
                self.refresh_data()
            except Exception as e:
                print(f"刷新數據失敗: {str(e)}")
                print("將使用現有數據")
        
        return {
            "sections": self.section_data,
        }
    
    def process_highway_data(self, api_data=None) -> Dict:
        """
        處理高速公路資料的接口方法
        
        參數:
            api_data (Dict, optional): 如果提供，使用提供的數據；否則使用已處理的數據
            
        返回:
            Dict: 處理後的高速公路資料
        """
        if api_data:
            sections = api_data.get("sections", {})
            live_traffic = api_data.get("liveTraffic", [])
            
            # 解析所有的路段資訊
            highways = {}
            
            for traffic in live_traffic:
                section_id = traffic.get('SectionID')
                if section_id not in sections:
                    continue
                    
                section_name = sections[section_id]
                
                # 解析路段名稱
                parts = section_name.split('(')
                if len(parts) < 2:
                    continue
                    
                highway = parts[0].strip()
                section_detail = parts[1].replace(')', '').strip()
                
                # 解析起點和終點
                section_parts = section_detail.split('到')
                if len(section_parts) < 2:
                    continue
                    
                from_point = section_parts[0].strip()
                to_point = section_parts[1].strip()
                
                # 建立路段資訊
                section_info = {
                    'sectionId': section_id,
                    'section': section_name,
                    'from': from_point,
                    'to': to_point,
                    'speed': traffic.get('TravelSpeed'),
                    'congestionDegree': traffic.get('CongestionLevel'),
                    'direction': ''  # 預設為空字串，後續補充
                }
                
                # 加入對應的高速公路資料結構，移除sections層級
                if highway not in highways:
                    highways[highway] = []
                
                highways[highway].append(section_info)
            
            # 補充方向資訊
            self._add_direction_info(highways)
            
            # 整合結果
            return {
                'highways': highways,
            }
        else:
            # 如果沒有提供新數據，確保已處理的數據是最新的
            if not self.processed_data:
                self._process_highway_data()
                
            return self.processed_data
    
    def _add_direction_info(self, highways: Dict) -> None:
        """
        根據給定的規則為每個路段添加方向信息
        
        參數:
            highways (Dict): 路段資訊字典
        """
        # 定義各高速公路的方向規則
        direction_rules = {
            "國道1號": [(0, 84, "南下"), (85, 169, "北上")],
            "汐五高架": [(0, 10, "南下"), (11, 21, "北上")],
            "國道2號": [(0, 5, "往鶯歌系統"), (6, 11, "往桃園機場")],
            "國道3號": [(0, 80, "南下"), (81, 161, "北上")],
            "國道3甲": [(0, 2, "往深坑"), (3, 5, "往木柵")],
            "台二己": [(0, 2, "往基金"), (3, 5, "往基隆港")],
            "國道4號": [(0, 6, "往潭子系統"), (7, 13, "往清水")],
            "國道5號": [(0, 5, "往蘇澳"), (6, 11, "往南港")],
            "國道6號": [(0, 7, "往埔里"), (8, 15, "往霧峰")],
            "國道8號": [(0, 4, "往新化"), (5, 9, "往台南")],
            "國道10號": [(0, 6, "往旗山"), (7, 13, "往左營")],
            "快速公路76號": [(0, 4, "往中興系統"), (5, 9, "往埔鹽系統")],
            "快速公路88號": [(0, 5, "往竹田系統"), (6, 11, "往五甲系統")]
        }
        
        # 為每個路段添加方向
        for highway_name, sections in highways.items():
            if highway_name == "國道1號":
                # 使用切片操作而不是在迭代中修改列表
                if len(sections) > 169:
                    highways[highway_name] = sections[:170]  # 取0到169的數據（共170個）
                sections = highways[highway_name]  # 更新sections引用
            if highway_name in direction_rules:
                for i, section in enumerate(sections):
                    for start, end, direction in direction_rules[highway_name]:
                        if start <= i <= end:
                            section['direction'] = direction
                            break

        
    
    def get_all_traffic_data(self) -> List[Dict[str, Any]]:
        """
        獲取所有高速公路交通資訊
        
        返回:
            List[Dict[str, Any]]: 所有高速公路路段的交通資訊清單
        """
        # 如果數據可能已過期，嘗試刷新
        if not self.last_refresh_time or datetime.now() - self.last_refresh_time > timedelta(seconds=self.cache_duration):
            try:
                print("數據可能已過期，嘗試刷新...")
                self.refresh_data()
            except Exception as e:
                print(f"刷新數據失敗: {str(e)}")
                print("將使用現有數據")
        
        results = []
        
        for traffic in self.traffic_data.get('LiveTraffics', []):
            section_id = traffic.get('SectionID')
            if section_id in self.section_data:
                section_info = {
                    "路段名稱": self.section_data[section_id],
                    "平均時速": traffic.get('TravelSpeed'),
                    "壅塞程度": traffic.get('CongestionLevel')
                }
                results.append(section_info)
        
        return results


# 如果直接執行這個檔案，則作為示範運行
if __name__ == "__main__":
    
    # 初始化服務
    highway_service = HighwayService()
    
    # 從API獲取資料
    api_data = highway_service.fetch_highway_data()
    
    # 處理資料
    if api_data:
        processed_data = highway_service.process_highway_data(api_data)
        #print(processed_data['highways']['國道1號'])