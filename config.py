"""Конфигурация приложения для анализа новостей.

Все настройки загружаются из .env файла для обеспечения безопасности.
Никаких захардкоженных значений - все параметры должны быть в .env файле.
"""

import os
from dotenv import load_dotenv

# Определяем базовую директорию проекта
basedir = os.path.abspath(os.path.dirname(__file__))
# Загружаем переменные окружения из .env файла
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    """Класс конфигурации приложения.
    
    Все настройки берутся из переменных окружения (.env файл).
    Если переменная не найдена, возвращается None - это заставляет
    правильно настроить все необходимые параметры.
    """
    # Настройки ClickHouse
    CLICKHOUSE_HOST = os.environ.get('CLICKHOUSE_HOST')
    CLICKHOUSE_PORT = int(os.environ.get('CLICKHOUSE_PORT')) if os.environ.get('CLICKHOUSE_PORT') else None
    CLICKHOUSE_NATIVE_PORT = int(os.environ.get('CLICKHOUSE_NATIVE_PORT')) if os.environ.get('CLICKHOUSE_NATIVE_PORT') else None
    CLICKHOUSE_USER = os.environ.get('CLICKHOUSE_USER')
    CLICKHOUSE_PASSWORD = os.environ.get('CLICKHOUSE_PASSWORD')
    CLICKHOUSE_DATABASE = os.environ.get('CLICKHOUSE_DATABASE', 'news')
    
    # Настройки Flask
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Настройки Telegram API
    TELEGRAM_API_ID = os.environ.get('TELEGRAM_API_ID')
    TELEGRAM_API_HASH = os.environ.get('TELEGRAM_API_HASH')
    TELEGRAM_PHONE = os.environ.get('TELEGRAM_PHONE')
    TELEGRAM_PASSWORD = os.environ.get('TELEGRAM_PASSWORD')
    
    # Настройки Twitter API
    TWITTER_BEARER_TOKEN = os.environ.get('TWITTER_BEARER_TOKEN')
    TWITTER_API_KEY = os.environ.get('TWITTER_API_KEY')
    TWITTER_API_SECRET = os.environ.get('TWITTER_API_SECRET')
    TWITTER_ACCESS_TOKEN = os.environ.get('TWITTER_ACCESS_TOKEN')
    TWITTER_ACCESS_TOKEN_SECRET = os.environ.get('TWITTER_ACCESS_TOKEN_SECRET')
    
    # Настройки AI API
    DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    OPENROUTER_DEEPSEEK_R1_API_KEY = os.environ.get('OPENROUTER_DEEPSEEK_R1_API_KEY')
    AUTH_KEY_GIGA_CHAT = os.environ.get('AUTH_KEY_GIGA_CHAT')
    AI_IO_KEY = os.environ.get('AI_IO_KEY')
    
    # Настройки Cloud.ru Foundation Models API
    CLOUD_RU_API_KEY = os.environ.get('CLOUD_RU_API_KEY') or os.environ.get('API_KEY')
    CLOUD_MODEL_URL = os.environ.get('CLOUD_MODEL_URL', 'https://foundation-models.api.cloud.ru/v1/chat/completions')
    CLOUD_MODEL_TOKEN = os.environ.get('CLOUD_MODEL_TOKEN') or os.environ.get('CLOUD_RU_API_KEY') or os.environ.get('API_KEY')
    
    # Настройки для генерации датасета
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    
    # Настройки сайта
    SITE_URL = os.environ.get('SITE_URL')
    SITE_NAME = os.environ.get('SITE_NAME')
