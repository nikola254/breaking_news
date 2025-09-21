#!/usr/bin/env python3
import clickhouse_connect

def check_military_operations_data():
    client = clickhouse_connect.get_client(host='localhost', port=8123, username='default', password='')
    
    print('=== Проверка данных в ukraine_universal_news для military_operations ===')
    result = client.execute("""
    SELECT COUNT(*) as count, 
           MIN(published_date) as min_date, 
           MAX(published_date) as max_date
    FROM news.ukraine_universal_news 
    WHERE category = 'military_operations' 
    AND published_date >= today() - 7
    """)
    print(f'За последние 7 дней: {result}')

    result = client.execute("""
    SELECT published_date, title, category
    FROM news.ukraine_universal_news 
    WHERE category = 'military_operations' 
    ORDER BY published_date DESC
    LIMIT 5
    """)
    print('\n=== Последние 5 записей military_operations ===')
    for row in result:
        print(f'{row[0]} | {row[1][:50]}... | {row[2]}')

    print('\n=== Проверка всех категорий в ukraine_universal_news ===')
    result = client.execute("""
    SELECT category, COUNT(*) as count
    FROM news.ukraine_universal_news 
    GROUP BY category
    ORDER BY count DESC
    """)
    for row in result:
        print(f'{row[0]}: {row[1]}')
        
    print('\n=== Проверка данных за последние 30 дней ===')
    result = client.execute("""
    SELECT COUNT(*) as count
    FROM news.ukraine_universal_news 
    WHERE category = 'military_operations' 
    AND published_date >= today() - 30
    """)
    print(f'За последние 30 дней: {result}')

if __name__ == "__main__":
    check_military_operations_data()