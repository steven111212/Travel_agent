import requests
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GOOGLE_MAPS_API_KEY  # 直接導入根目錄的 config.py

class LocationAPI:
    """Google Maps API 封裝"""
    
    def __init__(self):
        self.api_key = GOOGLE_MAPS_API_KEY
    
    def get_place_info(self, place_name):

        #台北特殊處理
        Taipei_list = ['台北', '台北市', '臺北', '臺北市']
        if place_name in Taipei_list:
            return ('臺北市', None)
        """
        使用Google Places API查询地点信息
        
        参数:
        place_name (str): 要查询的地点名称，例如 "千巧谷"
        api_key (str): Google Places API密钥
        
        返回:
        dict: 包含地点信息的字典
        """
        # 设置API端点和参数
        base_url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            "input": place_name,
            "inputtype": "textquery",
            "fields": "formatted_address,name,geometry,place_id",
            "language": "zh-TW",  # 设置返回结果为繁体中文
            "key": self.api_key
        }
        
        # 发送请求
        response = requests.get(base_url, params=params)
        results = response.json()
        result = results['candidates'][0]['formatted_address']

        city_list = [
            '台北市', '新北市', '基隆市', '桃園市', '新竹市', '新竹縣',
            '苗栗縣', '台中市', '彰化縣', '南投縣', '雲林縣', '嘉義市',
            '嘉義縣', '台南市', '高雄市', '屏東縣', '宜蘭縣', '花蓮縣',
            '台東縣', '澎湖縣', '金門縣', '連江縣',
            # 另一種寫法
            '臺北市', '臺中市', '臺南市', '臺東縣'
        ]
        # 提取縣市
        city = None
        for c in city_list:
            if c in result:
                city = c
                break
        city_index = result.index(city)
        city_after = result[city_index+len(city):]
        location = ['區', '鄉', '鎮', '市']
        location_name = None
        for i in location:
            location_index = city_after.find(i)
            if location_index > 0:
                location_name = city_after[:location_index+1]
                break
        return (city, location_name)