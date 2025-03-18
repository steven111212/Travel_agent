import logging
from services import WeatherService, WeatherAnalysisService

logger = logging.getLogger(__name__)

def display_weather_trend(forecast_data):
    """以ASCII圖表顯示天氣趨勢"""

    output_messages = ""
    
    print("\n==== 未來天氣趨勢 ====")
    output_messages += "\n==== 未來天氣趨勢 ===="
    
    # 顯示日期標頭
    date_header = " " * 10
    for day in forecast_data:
        date_header += f"{day['日期'][5:]} "
    print(date_header)
    output_messages += date_header

    
    # 顯示天氣圖示
    weather_icons = " " * 10
    for day in forecast_data:
        if "晴" in day['天氣現象']:
            weather_icons += " ☀️    "
        elif "雨" in day['天氣現象']:
            weather_icons += " 🌧️    "
        elif "陰" in day['天氣現象']:
            weather_icons += " ☁️    "
        else:
            weather_icons += " 🌤️    "
    print(weather_icons)
    output_messages += weather_icons
    
    # 顯示溫度
    temp_line = "溫度(°C): "
    for day in forecast_data:
        temp_line += f" {day['平均溫度']:2d}°  "
    print(temp_line)
    output_messages += temp_line
    
    # 顯示降雨機率
    rain_line = "降雨(%):  "
    for day in forecast_data:
        if not isinstance(day['降雨機率'], str):
            rain_line += f" {day['降雨機率']:2d}%  "
        else:
            rain_line += f"  -   "
    print(rain_line)
    output_messages += rain_line
    # 戶外適宜度
    suitability_line = "戶外適宜: "
    for day in forecast_data:
        if day['適宜度分數'] > 80:
            suitability_line += " 👍   "
        elif day['適宜度分數'] > 60:
            suitability_line += " 🙂   "
        elif day['適宜度分數'] > 40:
            suitability_line += " 😐   "
        else:
            suitability_line += " 👎   "
    print(suitability_line)
    output_messages += suitability_line
    return output_messages
 

def run_interactive_weather_query():
    """執行互動式天氣查詢對話"""
    # 建立服務實例
    weather_service = WeatherService()
    analysis_service = WeatherAnalysisService()
    
    print("\n=== 歡迎使用台灣旅遊天氣助手 ===")
    print("請輸入您想查詢的地點和時間")
    print("輸入 'stop' 結束對話\n")
    
    while True:
        try:
            # 獲取用戶輸入
            user_input = input("請問您想查詢哪裡的天氣？ ").strip()
            
            # 檢查是否要結束對話
            if user_input.lower() == 'stop':
                print("\n謝謝使用，再見！")
                break
            
            # 檢查是否有輸入內容
            if not user_input:
                print("請輸入查詢內容")
                continue
            
            # 處理查詢
            result = weather_service.query_weather(user_input)
            
            if result['查詢類型'] == '單日':
                # 處理單日查詢
                weather_info = weather_service.get_single_day_weather(result)
                
                # 輸出結果
                print(f"\n查詢結果:")
                print(f"\n🌏 地點: {weather_info['city']} - {weather_info['district']}")
                print(f"📅 時間: {weather_info['date']} {weather_info['time']}")
                print(f"🌤 天氣狀況: {weather_info['weather_description']}")
                print(f"🌅 日出時間: {weather_info['sunrise']} | 🌇 日落時間: {weather_info['sunset']}")
                
                # 顯示天氣警示
                analysis_service.check_weather_warnings(weather_info['notices'])
                
            else:
                # 處理多日查詢
                forecast_data = weather_service.get_multi_day_weather(result)
                
                # 顯示結果
                display_weather_trend(forecast_data)

                start_date = forecast_data[0]['日期']
                end_date = forecast_data[-1]['日期']
                print(f"\n🗓️ 查詢期間: {start_date} 至 {end_date}")
                print("-----------------------------------------------------------")

                # 輸出每一天的天氣資訊
                for day in forecast_data:
                    # 基本天氣資訊
                    print(f"\n📅 日期: {day['日期']}")
                    print(f"🌤 天氣狀況: {day['天氣現象']}")
                    print(f"🌡️ 溫度區間: {day['最低溫度']}°C - {day['最高溫度']}°C")
                    # 降雨機率信息
                    if not isinstance(day['降雨機率'], str):
                        rain_prob = day['降雨機率']
                        if rain_prob > 70:
                            print(f"☔ 降雨機率: {rain_prob}% (很可能下雨，請攜帶雨具)")
                        elif rain_prob > 30:
                            print(f"☂️ 降雨機率: {rain_prob}% (可能會下雨，建議準備雨具)")
                        else:
                            print(f"☀️ 降雨機率: {rain_prob}% (降雨機率低)")
                    
                    # 舒適度
                    if '舒適度' in day:
                        comfort = day['舒適度'].strip()
                        print(f"😌 舒適程度: {comfort}")

                    # 溫度提醒 (最高溫度<15°C時才提醒)
                    if day['最低溫度']<=15:
                        print(f"❄️ 注意: 天氣寒冷，請穿著保暖衣物！")
                    # 溫度提醒 (最高溫度>30°C時才提醒)
                    if day['最高溫度']>=30:
                        print(f"☀️ 注意: 天氣炎熱，需適時補充水分避免中暑，請做好防曬措施")
                    # 風速提醒 (風速5級以上才提醒)
                    if day['風速'] >= 5:
                        print(f"💨 注意: {day['風向'].strip()} 風速達{day['風速']}級，外出時請留意，應避免海邊、登山活動")
                    
                    # 紫外線提醒 (紫外線指數6以上才提醒)
                    if '紫外線指數' in day and day['紫外線指數'] >= 6:
                        print(f"☀️ 注意: 紫外線指數為{day['紫外線指數']}，請做好防曬措施")
                        
                    # 其他特別提醒 (可以根據天氣現象添加)
                    if "雷" in day['天氣現象']:
                        print("⚡ 注意: 有雷雨可能，請避免在戶外開闊地區活動")
                    
                    print("-----------------------------------------------------------")
        except Exception as e:
            logger.error(f"查詢處理錯誤: {e}")
            print(f"抱歉，查詢過程中發生錯誤: {str(e)}")
            print("請重新輸入查詢\n")



if __name__ == "__main__":
    # 設定日誌
    logging.basicConfig(level=logging.INFO)
    # 運行主程式
    run_interactive_weather_query()