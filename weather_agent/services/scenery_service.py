import sqlite3
import os


class SceneryService:
    # 初始化服務並連接資料庫
    def __init__(self):
        self.dict_location = {}
        db_path = 'scenic_indoor_spots.db'
        print(f"嘗試連接資料庫: {os.path.abspath(db_path)}")
        print(f"資料庫檔案是否存在: {os.path.exists(os.path.abspath(db_path))}")

        try:
            # 連接到資料庫
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                # 使用正確的表格名稱
                table_name = 'scenic_spots'  # 實際名稱
                cursor.execute(f"SELECT * FROM {table_name}")
                indoor_spots = cursor.fetchall()

                # 按位置分組景點數據
                for i in indoor_spots:
                    if i[6] not in self.dict_location:
                        self.dict_location[i[6]] = [i]
                    else:
                        self.dict_location[i[6]].append(i)
                
                # 按評分排序每個位置的景點
                for i in self.dict_location.keys():
                    data = sorted(self.dict_location[i], key=lambda x: int(x[8]) if x[8] != '' else 0, reverse=True)
                    self.dict_location[i] = data
                    
        except sqlite3.Error as e:
            print(f"資料庫錯誤: {e}")
            self.dict_location = {}
    
    # 獲取所有位置的景點
    def get_all_locations(self):
        return self.dict_location
    
    # 獲取特定位置的景點
    def get_location_spots(self, location):
        return self.dict_location.get(location, [])