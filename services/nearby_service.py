import sys
import os
import googlemaps
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GOOGLE_MAPS_API_KEY

class NearbyService:
    def __init__(self, api_key=GOOGLE_MAPS_API_KEY):
        self.gmaps = googlemaps.Client(key=api_key)

    def _get_coordinates(self, location):
        geocode_result = self.gmaps.geocode(location)
        location = geocode_result[0]['geometry']['location']
        lat_lng = (location['lat'], location['lng'])

        return lat_lng

    def _get_nearby_places(self, location, keyword):
        """
        Get nearby places based on the provided location and radius.

        :param location: Tuple of latitude and longitude (lat, lng).
        :param radius: Search radius in meters.
        :param place_type: Type of place to search for (e.g., 'restaurant', 'cafe').
        :return: List of nearby places.
        """
        try:
            lat_lng = self._get_coordinates(location)
            places = self.gmaps.places_nearby(
            location = lat_lng,
            radius = 2000,
            keyword=keyword,
            language='zh-tw'
        )
            return places.get('results', [])
        except Exception as e:
            print(f"Error fetching nearby places: {e}")
            return []
        
if __name__ == '__main__':
    nearby_service = NearbyService()
    location = '一中街'  # Example coordinates for Taichung, Taiwan
    keyword = '咖啡廳'
    nearby_places = nearby_service._get_nearby_places(location, keyword)
    #print(nearby_places)

    def format_places_response(places_data, top_n: int = 10) -> str:
        """格式化餐廳搜尋結果的回應文字"""
        response = "\n🔍 查詢結果如下：\n"

        for i, place in enumerate(places_data[:top_n], 1):
            name = place.get("name", "無名稱")
            address = place.get("vicinity", "無地址")
            rating = place.get("rating", "無評分")
            total_ratings = place.get("user_ratings_total", 0)
            is_open = place.get("opening_hours", {}).get("open_now", None)
            open_status = "🟢 營業中" if is_open else ("🔴 未營業" if is_open is not None else "⚪ 無營業資訊")
            lat = place["geometry"]["location"]["lat"]
            lng = place["geometry"]["location"]["lng"]
            map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
            
            response += f"\n📍 **推薦地點 {i}：{name}**"
            response += f"\n📌 地址：{address}"
            response += f"\n⭐ 評分：{rating}（{total_ratings} 則評論）"
            response += f"\n⏰ 營業狀態：{open_status}"
            response += f"\n🗺 地圖連結：{map_link}"
            response += "\n---------------------------------------"

        response += "\n🎉 以上是附近的美食推薦，希望你吃得開心！😋"
        return response
    
    print(format_places_response(nearby_places, 10))