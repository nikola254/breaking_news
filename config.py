import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    # Настройки ClickHouse
    CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST', 'localhost')
    CLICKHOUSE_PORT = int(os.environ.get('CLICKHOUSE_PORT', 8123))
    CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER', 'default')
    CLICKHOUSE_PASSWORD = os.environ.get('CLICKHOUSE_PASSWORD', '')
    
    # Другие настройки приложения
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-please-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Настройки для OpenRouter API
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
    SITE_URL = os.environ.get('SITE_URL', 'http://localhost:5000')
    SITE_NAME = os.environ.get('SITE_NAME', 'NewsAnalytics')