"""Модели данных и подключение к базе данных ClickHouse.

Этот модуль содержит:
- Конфигурацию подключения к ClickHouse
- Функции для создания клиентов базы данных
- Общие модели данных для работы с новостями
- Модели для анализа социальных сетей
"""

import clickhouse_connect
from config import Config

# Модели социальных сетей будут импортированы из отдельного модуля
# from app.models.social_models import *

# Получаем настройки из конфигурации
CLICKHOUSE_HOST = Config.CLICKHOUSE_HOST
# Используем HTTP порт для clickhouse_connect, а не нативный порт
CLICKHOUSE_PORT = Config.CLICKHOUSE_PORT  # HTTP порт 8123
CLICKHOUSE_USER = Config.CLICKHOUSE_USER
CLICKHOUSE_PASSWORD = Config.CLICKHOUSE_PASSWORD

def get_clickhouse_client():
    """Создание HTTP клиента для подключения к ClickHouse.
    
    Использует clickhouse_connect для HTTP подключения к ClickHouse.
    Это предпочтительный способ для веб-приложений.
    
    Returns:
        clickhouse_connect.Client: HTTP клиент ClickHouse
    """
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,  # Используем HTTP порт 8123
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD
    )