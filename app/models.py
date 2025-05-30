import clickhouse_connect
from config import Config

# Получаем настройки из конфигурации
CLICKHOUSE_HOST = Config.CLICKHOUSE_HOST
# Используем HTTP порт для clickhouse_connect, а не нативный порт
CLICKHOUSE_PORT = Config.CLICKHOUSE_PORT  # HTTP порт 8123
CLICKHOUSE_USER = Config.CLICKHOUSE_USER
CLICKHOUSE_PASSWORD = Config.CLICKHOUSE_PASSWORD

# Подключение к ClickHouse
def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,  # Используем HTTP порт 8123
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD
    )