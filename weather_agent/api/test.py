import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import GOOGLE_MAPS_API_KEY  # 直接導入根目錄的 config.py

print(GOOGLE_MAPS_API_KEY)