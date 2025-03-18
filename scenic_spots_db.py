import sqlite3
import json
import requests
import os
from datetime import datetime, timedelta
from config import CLIENT_ID, CLIENT_SECRET, LLM_BASE_URL, API_TYPE, MODEL, GOOGLE_MAPS_API_KEY
import litellm
import googlemaps

gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)

model = f"{API_TYPE}/{MODEL}"
# 在導入語句後添加
DB_PATH = "scenic_indoor_spots.db"
AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
API_BASE_URL = "https://tdx.transportdata.tw/api/basic/"

def get_auth_headers():
    global token_expiry, headers
    
    # 檢查令牌是否過期
    if not hasattr(get_auth_headers, "token_expiry") or datetime.now() > get_auth_headers.token_expiry:
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        response = requests.post(AUTH_URL, data=auth_data)
        auth_response = response.json()
        access_token = auth_response["access_token"]
        expires_in = auth_response.get("expires_in", 1800)
        get_auth_headers.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)
        get_auth_headers.headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    return get_auth_headers.headers

def create_database():
    """建立資料庫和表格結構"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 建立景點資料表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scenic_spots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ScenicSpotName TEXT,
        DescriptionDetail TEXT,
        Address TEXT,
        OpenTime TEXT,
        Picture TEXT,
        City TEXT,
        rating TEXT,
        comment_num TEXT,
        last_updated TIMESTAMP
    )
    ''')
    
    # 建立元數據表，用於追蹤上次更新時間
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS metadata (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def fetch_and_store_data():
    """從 API 獲取資料並存入資料庫"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    endpoint = f"v2/Tourism/ScenicSpot"
    url = f"{API_BASE_URL}{endpoint}"
    params = {
        "$format": "JSON",
        "$select": "ScenicSpotName,DescriptionDetail,Address,OpenTime,Picture,City"
    }
    
    headers = get_auth_headers()
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    data_indoor = []
    k = 0
    for i in data:
        message = f"{i['ScenicSpotName']}\n{i['DescriptionDetail']}"
        intent_messages = [
                {"role": "system", "content": "你是一個專門評估景點是否適合在雨天遊玩的助手。當用戶提供一個景點的資訊時，你只需要判斷該景點是否適合在下雨天去遊玩，不用給任何理由。只需要回答'是'或'否'。"},
                {"role": "user", "content": message}
            ]
        intent_response = litellm.completion(
                api_base = LLM_BASE_URL,
                api_key = 'ollama',
                model=model,
                messages=intent_messages,
            )           
        intent_result = intent_response.choices[0].message.content.strip().lower()
        print(i['ScenicSpotName'])
        print(intent_result)
        if '是' in intent_result:
            
            location_name = i.get('City','')+i['ScenicSpotName']
            place_search = gmaps.find_place(
                input=location_name,  # 農場名稱
                input_type="textquery",
                fields=["place_id", "name", "formatted_address"]
                )
            if place_search['status'] == 'OK' and len(place_search['candidates']) > 0:
                place_id = place_search['candidates'][0]['place_id']

                place_details = gmaps.place(
                place_id=place_id,
                language="zh-TW",  # 指定回傳繁體中文結果
                fields=["name", "rating", "user_ratings_total", "reviews"]
            )
                # 獲取評分資訊
                if 'result' in place_details:
                    result = place_details['result']

                    # 顯示評分(如果有)
                    if 'rating' in result:
                        rating = result['rating']
                        total_ratings = result.get('user_ratings_total', 0)
                        i['rating'] = rating
                        i['comment_num'] = total_ratings
                    else:
                        i['rating'] = 0
                        i['comment_num'] =0
            print(f"評分：{rating}， 評論數：{total_ratings}")
            data_indoor.append(i)

        k +=1
        if k%100==0:
            print(k)
            print(i)
    
    # 記錄當前時間作為更新時間戳
    current_time = datetime.now().isoformat()
    
    # 存儲資料
    for spot in data_indoor:
        cursor.execute('''
        INSERT OR REPLACE INTO scenic_spots
        (ScenicSpotName, DescriptionDetail, Address, OpenTime,Picture,City,rating, comment_num, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            spot.get('ScenicSpotName', ''),
            spot.get('DescriptionDetail', ''),
            spot.get('Address', ''),
            spot.get('OpenTime', ''),
            spot.get('Picture', '').get('PictureUrl1',''),
            spot.get('City', ''),
            spot.get('rating',''),
            spot.get('comment_num',''),
            current_time
        ))
    
    # 更新元數據中的最後更新時間
    cursor.execute('''
    INSERT OR REPLACE INTO metadata (key, value)
    VALUES ('last_update', ?)
    ''', (current_time,))
    
    conn.commit()
    conn.close()
    
    print(f"成功從 API 獲取並存儲 {len(data_indoor)} 筆景點資料")

def get_scenic_spots_from_db(filters=None):
    """從資料庫獲取景點資料，可根據條件過濾"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 這使得我們能夠通過列名訪問結果
    cursor = conn.cursor()
    
    query = "SELECT * FROM scenic_spots"
    params = []
    
    # 如果有過濾條件，加入 WHERE 子句
    if filters:
        where_clauses = []
        for key, value in filters.items():
            if key in ["ScenicSpotName", "Address"]:
                where_clauses.append(f"{key} LIKE ?")
                params.append(f"%{value}%")
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
    
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return results

def should_update_data(update_interval_days=7):
    """檢查是否需要更新資料"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT value FROM metadata WHERE key='last_update'")
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return True
    
    last_update = datetime.fromisoformat(result[0])
    days_since_update = (datetime.now() - last_update).days
    
    return days_since_update >= update_interval_days

def main():
    # 確保資料庫存在
    if not os.path.exists(DB_PATH):
        create_database()
    
    # 檢查是否需要更新資料
    if should_update_data():
        print("資料需要更新，正在從 API 獲取新資料...")
        fetch_and_store_data()
    else:
        print("使用本地資料庫中的資料")
    
    # 示範如何從資料庫獲取資料
    # 例如獲取名稱中含有「公園」的景點
    parks = get_scenic_spots_from_db({"ScenicSpotName": "公園"})
    print(f"找到 {len(parks)} 個包含「公園」的景點")
    for park in parks[:3]:  # 只顯示前3個作為示例
        print(f"名稱: {park['ScenicSpotName']}, 地址: {park['Address']}")

if __name__ == "__main__":
    main()