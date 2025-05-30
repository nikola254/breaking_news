#!/bin/bash

# Порог в байтах (15 ГБ)
DISK_LIMIT=$((15 * 1024 * 1024 * 1024))
CLICKHOUSE_CLI="clickhouse-client --host 127.0.0.1 --port 9000"

# Путь к данным ClickHouse
DATA_PATH="/var/lib/clickhouse"

# Имя базы данных и таблицы
DATABASE="your_database"
TABLE="your_table"

# Лог-файл
LOG_FILE="/var/log/clickhouse_cleanup.log"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

log "Начало проверки использования диска"

# Получаем текущий размер данных
CURRENT_SIZE=$(du -sb "$DATA_PATH" | awk '{print $1}')

if [ "$CURRENT_SIZE" -gt "$DISK_LIMIT" ]; then
    log "Превышение лимита диска: $((CURRENT_SIZE / 1024 / 1024 / 1024)) ГБ > 15 ГБ"

    # Пример: удаляем самые старые 1000 строк
    # Измените условие WHERE под ваши нужды (например, по дате)
    $CLICKHOUSE_CLI --query="ALTER TABLE $DATABASE.$TABLE DELETE WHERE event_date < now() - INTERVAL 30 DAY LIMIT 1000"

    log "Выполнено удаление старых записей"
else
    log "Использование диска в норме: $((CURRENT_SIZE / 1024 / 1024 / 1024)) ГБ"
fi