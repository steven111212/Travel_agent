import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
API_TYPE = os.getenv('API_TYPE')
MODEL = os.getenv('MODEL')
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')

# LLM Configuration
LLM_CONFIG = {
    "model": MODEL,
    "base_url": LLM_BASE_URL,
    "api_key": LLM_API_KEY,
    "temperature": 0.2,
}

# Other configurations
DEFAULT_LANGUAGE = "zh-TW"
DATABASE_PATH = "data/scenic_indoor_spots.db"
LOCATIONS_JSON_PATH = "data/locations.json"
HIGHWAY_DATA_PATH = "data/highway_mapping.json"
CITY_MAP_JSON_PATH = "data/city_map.json"

# LangChain specific configurations
MAX_TOKENS = 500
INTENT_CLASSIFICATION_TEMPERATURE = 0.1
GENERAL_RESPONSE_TEMPERATURE = 0.7