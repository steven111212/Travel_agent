import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# API 金鑰
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")

# 其他配置項
DEFAULT_LANGUAGE = "zh-TW"

