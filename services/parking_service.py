import sys
import os
import googlemaps
import requests
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CLIENT_ID, CLIENT_SECRET, GOOGLE_MAPS_API_KEY


class ParkingService:
    def __init__(self):
        self.gmaps = googlemaps.Client(key= GOOGLE_MAPS_API_KEY)
        self.max_retries = 3       # 最大重試次數
        self.access_token = None
        self.base_url = "https://tdx.transportdata.tw/api/advanced/v1/Parking/"

    def _get_parking_information(self, address, radius=500):
        """
        獲取指定地址的停車場資訊
        
        參數:
        - address: 想要查詢的地址字符串
        - parking_type: 停車場類型，可以是 "OffStreet" (路外停車場) 或 "OnStreet" (路邊停車格)
        - radius: 搜尋半徑 (公尺)
        
        返回:
        - 停車場資訊列表
        """
        self._get_access_token()  # 獲取訪問令牌
        # 獲取地址的經緯度

        longitude, latitude = self._get_coordinates(address)
        
        if longitude is None or latitude is None:
            return None
        
        # 獲取附近停車場資訊
        parking_info = self._find_nearby_parking(longitude, latitude, radius)
        
        return parking_info

    def _get_access_token(self):
        """
        獲取訪問令牌
        :return: 訪問令牌
        """
        AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        payload = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
        response = requests.post(AUTH_URL, data=payload)
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            return 
        else:
            raise Exception(f"獲取 token 失敗: {response.text}")

    
    def _get_coordinates(self, address):
        """
        使用 Google Maps API 獲取地址的經緯度
        
        參數:
        - address: 想要查詢的地址字符串
        
        返回:
        - 經度, 緯度: 如果查詢成功
        - None, None: 如果查詢失敗
        """
        try:
            places_result = self.gmaps.places(address, language='zh-TW')
        
            # 檢查結果是否有效
            if places_result and 'results' in places_result and places_result['results']:
                location = places_result['results'][0]['geometry']['location']
                latitude = location['lat']
                longitude = location['lng']
                return longitude, latitude
            else:
                print(f"找不到地址: {address}")
                return None, None
            
        except Exception as e:
            print(f"查詢地址時發生錯誤: {e}")
            return None, None
        
    def _find_nearby_parking(self, longitude, latitude, radius=500):
        # 使用預設設定的最大重試次數
        for attempt in range(self.max_retries):
            try:
                headers = {
                    'Authorization': f'Bearer {self.access_token}',
                }
                
                endpoint = f"{self.base_url}OffStreet/CarPark/NearBy"
                
                params = {
                    '$spatialFilter': f'nearby({latitude}, {longitude}, {radius})',
                    '$format': 'JSON'
                }
                
                response = requests.get(endpoint, headers=headers, params=params)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:  # Token 過期
                    self._get_access_token()  # 重新獲取 token
                else:
                    print(f"請求失敗 (嘗試 {attempt+1}/{self.max_retries}): {response.status_code}")
                    
            except Exception as e:
                print(f"發生錯誤 (嘗試 {attempt+1}/{self.max_retries}): {e}")
            
            # 如果這不是最後一次嘗試，等待一下再重試
            if attempt < self.max_retries - 1:
                import time
                time.sleep(2)  # 等待 2 秒再重試
        
        # 所有嘗試都失敗
        raise Exception("獲取停車場資訊失敗：已達最大重試次數")