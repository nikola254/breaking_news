"""Скрипт для проверки статистики базы данных"""
from clickhouse_driver import Client
from config import Config

def check_stats():
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    print("\n" + "=" * 60)
    print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    tables = {
        'lenta_headlines': 'Lenta.ru',
        'rbc_headlines': 'RBC.ru',
        'gazeta_headlines': 'Gazeta.ru',
        'kommersant_headlines': 'Kommersant',
        'cnn_headlines': 'CNN',
        'bbc_headlines': 'BBC'
    }
    
    total = 0
    
    for table, name in tables.items():
        try:
            result = client.execute(f'SELECT COUNT(*) FROM news.{table}')
            count = result[0][0]
            total += count
            if count > 0:
                print(f"📰 {name:20} {count:6} новостей")
        except Exception as e:
            if "doesn't exist" not in str(e):
                print(f"⚠️  {name:20} ошибка: {e}")
    
    print("=" * 60)
    print(f"✅ ВСЕГО: {total} новостей")
    print("=" * 60)
    
    # Статистика по категориям
    print("\n📑 ПО КАТЕГОРИЯМ:")
    print("=" * 60)
    
    try:
        query = """
        SELECT category, COUNT(*) as cnt
        FROM news.lenta_headlines
        GROUP BY category
        ORDER BY cnt DESC
        """
        results = client.execute(query)
        
        for category, count in results:
            print(f"  {category:30} {count:6}")
            
    except Exception as e:
        print(f"⚠️  Ошибка: {e}")
    
    print("=" * 60 + "\n")

if __name__ == '__main__':
    check_stats()



