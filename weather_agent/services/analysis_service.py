from typing import List, Dict, Any
import re

class WeatherAnalysisService:
    """天氣分析服務"""
    
    def evaluate_outdoor_suitability(self, forecast_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """評估哪幾天適合戶外活動"""
        # 您原有的 evaluate_outdoor_suitability 方法內容
        for day_data in forecast_data:
            score = 100  # 滿分100
            
            # 根據降雨機率降分
            if not isinstance(day_data['降雨機率'], str):
                if day_data['降雨機率'] > 70:
                    score -= 60
                elif day_data['降雨機率'] > 30:
                    score -= 30
            
            # 根據溫度適宜度評分
            temp = day_data['平均溫度']
            if temp < 15 or temp > 30:
                score -= 20
            
            # 根據風速評分
            if day_data['風速'] > 6:  # 假設風速單位為m/s
                score -= 15
            
            # 根據天氣現象評分
            weather_desc = day_data['天氣現象']
            if any(bad_weather in weather_desc for bad_weather in ["雷", "暴雨", "豪雨", "颱風"]):
                score -= 50
            
            day_data["適宜度分數"] = score
            day_data["適宜度評價"] = "非常適合" if score > 80 else "適合" if score > 60 else "尚可" if score > 40 else "不建議"
        
        return forecast_data
    
    def check_weather_warnings(self, data):
        warnings = []
        
        # 檢查每個天氣描述項目
        for item in data:
            # 檢查是否有雷雨
            if '雷' in item:
                warnings.append("⚡ 注意: 有雷雨可能，請避免在戶外開闊地區活動")
            
            # 檢查風速
            if '風速' in item:
                # 解析風速
                wind_match = re.search(r'風速.*?(\d+)級', item)
                if wind_match:
                    wind_level = int(wind_match.group(1))
                    if wind_level >= 5:
                        warnings.append("💨 注意: 風速達5級以上，外出時請留意，應避免海邊、登山活動")
            
            # 檢查溫度
            if '溫度' in item or '攝氏' in item:
                # 解析最高溫度
                temp_match = re.search(r'溫度攝氏(\d+)至(\d+)度', item)
                if temp_match:
                    min_temp = int(temp_match.group(1))
                    max_temp = int(temp_match.group(2))
                    if max_temp >= 30:
                        warnings.append("☀️ 注意: 天氣炎熱，需適時補充水分避免中暑，請做好防曬措施")
            
            # 檢查降雨機率
            if '降雨機率' in item:
                # 解析降雨機率
                rain_match = re.search(r'降雨機率(\d+)%', item)
                if rain_match:
                    rain_prob = int(rain_match.group(1))
                    if rain_prob >= 70:
                        warnings.append(f"☔ 注意 降雨機率達{rain_prob}% (很可能下雨，請攜帶雨具)")
                    elif 30 <= rain_prob < 70:
                        warnings.append(f"☂️ 注意 降雨機率達{rain_prob}%(可能會下雨，建議準備雨具)")
        
        # 輸出所有警告
        for warning in warnings:
            print(warning)
            
        return warnings, rain_prob