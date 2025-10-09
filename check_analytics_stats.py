#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from clickhouse_driver import Client
from config import Config

def check_statistics():
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=Config.CLICKHOUSE_DATABASE
    )

    print('Проверяем статистику из раздела Аналитика (за последние 7 дней):')
    print()

    # Проверяем данные за последние 7 дней из всех таблиц
    tables = [
        'telegram_headlines',
        'ria_headlines', 
        'lenta_headlines',
        'rbc_headlines',
        'cnn_headlines',
        'reuters_headlines',
        'aljazeera_headlines',
        'bbc_headlines',
        'dw_headlines',
        'euronews_headlines',
        'france24_headlines',
        'gazeta_headlines',
        'kommersant_headlines',
        'rt_headlines',
        'tsn_headlines',
        'unian_headlines'
    ]

    total_recent = 0
    for table in tables:
        try:
            query = f'SELECT COUNT(*) FROM news.{table} WHERE published_date >= today() - 7'
            result = client.execute(query)
            count = result[0][0] if result else 0
            if count > 0:
                print(f'{table}: {count} статей за последние 7 дней')
                total_recent += count
        except Exception as e:
            print(f'{table}: ошибка - {e}')

    print(f'\nВсего статей за последние 7 дней: {total_recent}')

    print()
    print('Статистика по категориям за последние 7 дней:')
    categories = ['military_operations', 'humanitarian_crisis', 'economic_consequences', 'political_decisions', 'information_social']

    for category in categories:
        total_cat = 0
        for table in tables:
            try:
                query = f"SELECT COUNT(*) FROM news.{table} WHERE published_date >= today() - 7 AND category = '{category}'"
                result = client.execute(query)
                count = result[0][0] if result else 0
                total_cat += count
            except:
                pass
        print(f'{category}: {total_cat} статей')

if __name__ == '__main__':
    check_statistics()
