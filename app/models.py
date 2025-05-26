import clickhouse_connect
from config import Config

# Получаем настройки из конфигурации
CLICKHOUSE_HOST = Config.CLICKHOUSE_HOST
CLICKHOUSE_PORT = Config.CLICKHOUSE_PORT
CLICKHOUSE_USER = Config.CLICKHOUSE_USER
CLICKHOUSE_PASSWORD = Config.CLICKHOUSE_PASSWORD

# Подключение к ClickHouse
def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD
    )