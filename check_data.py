#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from clickhouse_driver import Client
from config import Config

client = Client(
    host=Config.CLICKHOUSE_HOST,
    port=Config.CLICKHOUSE_NATIVE_PORT,
    user=Config.CLICKHOUSE_USER,
    password=Config.CLICKHOUSE_PASSWORD
)

print('Проверка дат записей в ukraine_universal_news:')

# Все записи с датами
result = client.execute('SELECT category, title, published_date FROM news.ukraine_universal_news ORDER BY published_date DESC')
print('\nВсе записи:')
for category, title, date in result:
    print(f'  {date} | {category} | {title[:50]}...')

# Записи за последние 7 дней
result = client.execute('SELECT category, COUNT(*) FROM news.ukraine_universal_news WHERE published_date >= today() - 7 GROUP BY category')
print('\nЗаписи за последние 7 дней:')
if result:
    for category, count in result:
        print(f'  {category}: {count} записей')
else:
    print('  Нет записей за последние 7 дней')

# Записи military_operations за последние 30 дней
result = client.execute("SELECT COUNT(*) FROM news.ukraine_universal_news WHERE category = 'military_operations' AND published_date >= today() - 30")
print(f'\nЗаписи military_operations за последние 30 дней: {result[0][0]}')

# Все записи military_operations
result = client.execute("SELECT COUNT(*) FROM news.ukraine_universal_news WHERE category = 'military_operations'")
print(f'Всего записей military_operations: {result[0][0]}')

# Проверим, есть ли данные в других таблицах
print('\n=== Проверка других таблиц ===')

# Проверим universal_military_operations
try:
    result = client.execute('SELECT COUNT(*) FROM news.universal_military_operations')
    print(f'universal_military_operations: {result[0][0]} записей')
    
    if result[0][0] > 0:
        result = client.execute('SELECT title, published_date FROM news.universal_military_operations ORDER BY published_date DESC LIMIT 5')
        print('  Последние записи:')
        for title, date in result:
            print(f'    {date}: {title[:50]}...')
except Exception as e:
    print(f'universal_military_operations: ошибка - {e}')

# Проверим telegram_headlines
try:
    result = client.execute("SELECT COUNT(*) FROM news.telegram_headlines WHERE category = 'military_operations'")
    print(f'telegram_headlines (military_operations): {result[0][0]} записей')
    
    if result[0][0] > 0:
        result = client.execute("SELECT title, published_date FROM news.telegram_headlines WHERE category = 'military_operations' ORDER BY published_date DESC LIMIT 5")
        print('  Последние записи:')
        for title, date in result:
            print(f'    {date}: {title[:50]}...')
except Exception as e:
    print(f'telegram_headlines: ошибка - {e}')