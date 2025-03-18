from ui import run_interactive_weather_query
from services import WeatherService, WeatherAnalysisService, SceneryService
import random

def recommand_indoor_scenery(location):

    scenery_service = SceneryService()
    return scenery_service.get_location_spots(location)

def display_weather_trend(forecast_data):
    """以ASCII圖表顯示天氣趨勢"""

    output_messages = ""
    
    #print("\n==== 未來天氣趨勢 ====")
    output_messages += "\n==== 未來天氣趨勢 ===="
    
    # 顯示日期標頭
    date_header = " " * 10
    for day in forecast_data:
        date_header += f"{day['日期'][5:]} "
    #print(date_header)
    output_messages += f"\n{date_header}"

    
    # 顯示天氣圖示
    weather_icons = " " * 10
    for day in forecast_data:
        if "晴" in day['天氣現象']:
            weather_icons += " ☀️   "
        elif "雨" in day['天氣現象']:
            weather_icons += " 🌧️   "
        elif "陰" in day['天氣現象']:
            weather_icons += " ☁️   "
        else:
            weather_icons += " 🌤️   "
    #print(weather_icons)
    output_messages += f"\n{weather_icons}"
    
    # 顯示溫度
    temp_line = "溫度(°C): "
    for day in forecast_data:
        temp_line += f" {day['平均溫度']:2d}°  "
    #print(temp_line)
    output_messages += f"\n{temp_line}"
    
    # 顯示降雨機率
    rain_line = "降雨(%):  "
    for day in forecast_data:
        if not isinstance(day['降雨機率'], str):
            rain_line += f" {day['降雨機率']:2d}%  "
        else:
            rain_line += f"  -   "
    #print(rain_line)
    output_messages += f"\n{rain_line}"
    # 戶外適宜度
    suitability_line = "戶外適宜: "
    for day in forecast_data:
        if day['適宜度分數'] > 80:
            suitability_line += " 👍  "
        elif day['適宜度分數'] > 60:
            suitability_line += " 🙂  "
        elif day['適宜度分數'] > 40:
            suitability_line += " 😐  "
        else:
            suitability_line += " 👎  "
    #print(suitability_line)
    output_messages += f"\n{suitability_line}"

    return output_messages

def weather_agent(query):
    """執行互動式天氣查詢對話"""
    # 建立服務實例
    weather_service = WeatherService()
    analysis_service = WeatherAnalysisService()
    result = weather_service.query_weather(query)
    output = ""      
    if result['查詢類型'] == '單日':
        # 處理單日查詢
        weather_info = weather_service.get_single_day_weather(result)
        
        # 輸出結果
        
        output += f"\n查詢結果:"
        output += f"\n🌏 地點: {weather_info['city']} - {weather_info['district']}"
        output += f"\n📅 時間: {weather_info['date']} {weather_info['time']}"
        output += f"\n🌤 天氣狀況: {weather_info['weather_description']}"
        output += f"\n🌅 日出時間: {weather_info['sunrise']} | 🌇 日落時間: {weather_info['sunset']}"

        # 顯示天氣警示
        warnings, rain_prob = analysis_service.check_weather_warnings(weather_info['notices'])
        for i in warnings:
            output +=i

        if rain_prob>= 30:
            recommand_data = recommand_indoor_scenery(weather_info['city'])
            output +=f"\n🌧 由於{weather_info['city'][:2]}有降雨的可能，我幫你挑選了一些室內或適合雨天的景點，希望你會喜歡！\n\n"
            if weather_info['city'][:2]=='基隆':
                output += f"📍 **推薦景點：{recommand_data[0][1]}**\n"
                output += f"🕒 **開放時間：{recommand_data[0][4]}**\n"
            else:
                random_numbers = random.sample(range(0, len(recommand_data)//3), len(recommand_data)//5)   #取前3分之1的景點作推薦
                n = 1
                for i in random_numbers:
                    output += f"📍 **推薦景點 {n}：{recommand_data[i][1]}**\n"
                    if recommand_data[i][4]:
                        output += f"🕒 **開放時間：{recommand_data[i][4]}**\n"
                    output += "---------------------------------\n"
                    n += 1
                    if n>5:  #最多推薦5個
                        break
            output += "✨ 希望這些景點能讓你的行程更豐富！不論晴天或雨天，都祝你玩得開心！☔😊"
            
    else:
        # 處理多日查詢
        forecast_data = weather_service.get_multi_day_weather(result)
        
        # 顯示結果
        output +=display_weather_trend(forecast_data)

        start_date = forecast_data[0]['日期']
        end_date = forecast_data[-1]['日期']
        #print(f"\n🗓️ 查詢期間: {start_date} 至 {end_date}")
        #print("-----------------------------------------------------------")
        output += f"\n🗓️ 查詢期間: {start_date} 至 {end_date}"
        output += "\n-----------------------------------------------------------"
        # 輸出每一天的天氣資訊
        for day in forecast_data:
            # 基本天氣資訊
            #print(f"\n📅 日期: {day['日期']}")
            #print(f"🌤 天氣狀況: {day['天氣現象']}")
            #print(f"🌡️ 溫度區間: {day['最低溫度']}°C - {day['最高溫度']}°C")
            output += f"\n📅 日期: {day['日期']}"
            output += f"\n🌤 天氣狀況: {day['天氣現象']}"
            output += f"\n🌡️ 溫度區間: {day['最低溫度']}°C - {day['最高溫度']}°C"
            # 降雨機率信息
            if not isinstance(day['降雨機率'], str):
                rain_prob = day['降雨機率']
                if rain_prob > 70:
                    #print(f"☔ 降雨機率: {rain_prob}% (很可能下雨，請攜帶雨具)")
                    output += f"\n☔ 降雨機率: {rain_prob}% (很可能下雨，請攜帶雨具)"
                elif rain_prob > 30:
                    #print(f"☂️ 降雨機率: {rain_prob}% (可能會下雨，建議準備雨具)")
                    output += f"\n☂️ 降雨機率: {rain_prob}% (可能會下雨，建議準備雨具)"
                else:
                    #print(f"☀️ 降雨機率: {rain_prob}% (降雨機率低)")
                    output +=f"\n☀️ 降雨機率: {rain_prob}% (降雨機率低)"
            
            # 舒適度
            if '舒適度' in day:
                comfort = day['舒適度'].strip()
                #print(f"😌 舒適程度: {comfort}")
                output +=f"\n😌 舒適程度: {comfort}"

            # 溫度提醒 (最高溫度<15°C時才提醒)
            if day['最低溫度']<=15:
                #print(f"❄️ 注意: 天氣寒冷，請穿著保暖衣物！")
                output +=f"\n❄️ 注意: 天氣寒冷，請穿著保暖衣物！"
            # 溫度提醒 (最高溫度>30°C時才提醒)
            if day['最高溫度']>=30:
                #print(f"☀️ 注意: 天氣炎熱，需適時補充水分避免中暑，請做好防曬措施")
                output +=f"\n☀️ 注意: 天氣炎熱，需適時補充水分避免中暑，請做好防曬措施"
            # 風速提醒 (風速5級以上才提醒)
            if day['風速'] >= 5:
                #print(f"💨 注意: {day['風向'].strip()} 風速達{day['風速']}級，外出時請留意，應避免海邊、登山活動")
                output +=f"\n💨 注意: {day['風向'].strip()} 風速達{day['風速']}級，外出時請留意，應避免海邊、登山活動"
            
            # 紫外線提醒 (紫外線指數6以上才提醒)
            if '紫外線指數' in day and day['紫外線指數'] >= 6:
                #print(f"☀️ 注意: 紫外線指數為{day['紫外線指數']}，請做好防曬措施")
                output += f"\n☀️ 注意: 紫外線指數為{day['紫外線指數']}，請做好防曬措施"
                
            # 其他特別提醒 (可以根據天氣現象添加)
            if "雷" in day['天氣現象']:
                #print("⚡ 注意: 有雷雨可能，請避免在戶外開闊地區活動")
                output +="\n⚡ 注意: 有雷雨可能，請避免在戶外開闊地區活動"
            
            #print("-----------------------------------------------------------")
            output +="\n-----------------------------------------------------------"

    return output

# if __name__ == "__main__":
#     run_interactive_weather_query()