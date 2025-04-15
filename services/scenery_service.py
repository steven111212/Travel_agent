import sqlite3
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_PATH
from typing import Dict, List, Any

class SceneryService:
    """Service for accessing scenic spot data from the database"""
    
    def __init__(self):
        """Initialize service and connect to database"""
        self.dict_location = {}
        db_path = DATABASE_PATH
        print(f"Attempting to connect to database: {os.path.abspath(db_path)}")
        print(f"Database file exists: {os.path.exists(os.path.abspath(db_path))}")

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Connect to database
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                # Use correct table name
                table_name = 'scenic_spots'  # Actual name
                
                cursor.execute(f"SELECT * FROM {table_name}")
                indoor_spots = cursor.fetchall()

                # Group spot data by location
                for i in indoor_spots:
                    if i[6] not in self.dict_location:
                        self.dict_location[i[6]] = [i]
                    else:
                        self.dict_location[i[6]].append(i)
                
                # Sort spots by rating for each location
                for i in self.dict_location.keys():
                    data = sorted(self.dict_location[i], key=lambda x: int(x[8]) if x[8] != '' else 0, reverse=True)
                    self.dict_location[i] = data
                    
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            self.dict_location = {}
    

    def get_all_locations(self) -> Dict[str, List[Any]]:
        """Get spots for all locations"""
        return self.dict_location
    
    def get_location_spots(self, location: str) -> List[Any]:
        """Get spots for a specific location"""
        return self.dict_location.get(location, [])
    
    
    