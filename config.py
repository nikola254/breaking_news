import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # Настройки ClickHouse
    CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST', '81.94.158.134')
    CLICKHOUSE_PORT = int(os.environ.get('CLICKHOUSE_PORT', 8123))
    CLICKHOUSE_NATIVE_PORT = int(os.environ.get('CLICKHOUSE_NATIVE_PORT', 9000))
    CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER', 'default')
    CLICKHOUSE_PASSWORD = os.environ.get('CLICKHOUSE_PASSWORD', '')
    
    # Другие настройки приложения
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Настройки для OpenRouter API
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
    OPENROUTER_DEEPSEEK_R1_API_KEY = os.environ.get('OPENROUTER_DEEPSEEK_R1_API_KEY', '')
    SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5000')
    SITE_NAME = os.environ.get('SITE_NAME', 'NewsAnalytics')
    
    # Настройки для AI.IO API
    AIIO_API_KEY = os.environ.get('AIIO_API_KEY', 'io-v2-eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJvd25lciI6ImVjODQ0MjA4LTVhMjYtNGEyZC1iZjc3LWI5MWM3YWM1NDBkZiIsImV4cCI6NDkwMjAwODMyMn0.KwUhPdVppnVNwtVYbQCUkm8AkbxRipaklZFf20OgWnVjV4Xmo2S4RIX73_j3B5JjdYh4HJI2QS1vvYACcDTxfg')
