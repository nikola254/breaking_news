"""
Скрипт для полного сброса и пересоздания базы данных ClickHouse
Удаляет все существующие таблицы и создает только необходимые для проекта
"""
from app.models import get_clickhouse_client
import sys

def drop_all_tables():
    """Удаляет все таблицы из базы данных news"""
    client = get_clickhouse_client()
    
    try:
        print("\n" + "=" * 60)
        print("ШАГ 1: УДАЛЕНИЕ ВСЕХ СУЩЕСТВУЮЩИХ ТАБЛИЦ")
        print("=" * 60)
        
        # Получаем список всех таблиц
        result = client.query("SELECT name FROM system.tables WHERE database = 'news'")
        tables = [row[0] for row in result.result_rows]
        
        print(f"\nНайдено {len(tables)} таблиц для удаления:")
        
        dropped_count = 0
        for table in tables:
            try:
                client.query(f"DROP TABLE IF EXISTS news.{table}")
                print(f"✓ Удалена таблица: {table}")
                dropped_count += 1
            except Exception as e:
                print(f"✗ Ошибка при удалении таблицы {table}: {str(e)}")
        
        print(f"\n✓ Удалено таблиц: {dropped_count}")
        
    finally:
        client.close()


def create_news_tables():
    """Создает основные таблицы для хранения новостей"""
    client = get_clickhouse_client()
    
    try:
        print("\n" + "=" * 60)
        print("ШАГ 2: СОЗДАНИЕ ОСНОВНЫХ ТАБЛИЦ НОВОСТЕЙ")
        print("=" * 60)
        
        # Определяем таблицы для основных источников новостей
        sources = {
            'ria': {
                'name': 'ria_headlines',
                'default_source': 'ria.ru'
            },
            'lenta': {
                'name': 'lenta_headlines',
                'default_source': 'lenta.ru'
            },
            'rbc': {
                'name': 'rbc_headlines',
                'default_source': 'rbc.ru'
            },
            'gazeta': {
                'name': 'gazeta_headlines',
                'default_source': 'gazeta.ru'
            },
            'kommersant': {
                'name': 'kommersant_headlines',
                'default_source': 'kommersant.ru'
            },
            'tsn': {
                'name': 'tsn_headlines',
                'default_source': 'tsn.ua'
            },
            'unian': {
                'name': 'unian_headlines',
                'default_source': 'unian.ua'
            },
            'rt': {
                'name': 'rt_headlines',
                'default_source': 'rt.com'
            },
            'cnn': {
                'name': 'cnn_headlines',
                'default_source': 'cnn.com'
            },
            'bbc': {
                'name': 'bbc_headlines',
                'default_source': 'bbc.com'
            },
            'aljazeera': {
                'name': 'aljazeera_headlines',
                'default_source': 'aljazeera.com'
            },
            'reuters': {
                'name': 'reuters_headlines',
                'default_source': 'reuters.com'
            },
            'france24': {
                'name': 'france24_headlines',
                'default_source': 'france24.com'
            },
            'dw': {
                'name': 'dw_headlines',
                'default_source': 'dw.com'
            },
            'euronews': {
                'name': 'euronews_headlines',
                'default_source': 'euronews.com'
            },
            'israil': {
                'name': 'israil_headlines',
                'default_source': '7kanal.co.il'
            }
        }
        
        created_count = 0
        for source_key, source_info in sources.items():
            table_name = source_info['name']
            default_source = source_info['default_source']
            
            create_query = f"""
            CREATE TABLE IF NOT EXISTS news.{table_name} (
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                rubric String DEFAULT '',
                source String DEFAULT '{default_source}',
                category String DEFAULT 'other',
                published_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY published_date
            """
            
            try:
                client.query(create_query)
                print(f"✓ Создана таблица: {table_name}")
                created_count += 1
            except Exception as e:
                print(f"✗ Ошибка при создании таблицы {table_name}: {str(e)}")
        
        print(f"\n✓ Создано таблиц: {created_count}")
        
    finally:
        client.close()


def create_telegram_tables():
    """Создает таблицы для Telegram"""
    client = get_clickhouse_client()
    
    try:
        print("\n" + "=" * 60)
        print("ШАГ 3: СОЗДАНИЕ ТАБЛИЦ TELEGRAM")
        print("=" * 60)
        
        # Категории для Telegram
        categories = [
            'military_operations',
            'humanitarian_crisis',
            'economic_consequences',
            'political_decisions',
            'information_social'
        ]
        
        created_count = 0
        
        # Создаем таблицы для каждой категории
        for category in categories:
            table_name = f'telegram_{category}'
            
            create_query = f"""
            CREATE TABLE IF NOT EXISTS news.{table_name} (
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String DEFAULT '',
                content String,
                channel String,
                message_id Int64,
                message_link String,
                source String DEFAULT 'telegram',
                category String DEFAULT '{category}',
                published_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY published_date
            """
            
            try:
                client.query(create_query)
                print(f"✓ Создана таблица: {table_name}")
                created_count += 1
            except Exception as e:
                print(f"✗ Ошибка при создании таблицы {table_name}: {str(e)}")
        
        # Создаем общую таблицу telegram_headlines
        create_headlines_query = """
        CREATE TABLE IF NOT EXISTS news.telegram_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String DEFAULT '',
            content String,
            channel String,
            message_id Int64,
            message_link String,
            source String DEFAULT 'telegram',
            category String DEFAULT 'other',
            published_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY published_date
        """
        
        try:
            client.query(create_headlines_query)
            print(f"✓ Создана таблица: telegram_headlines")
            created_count += 1
        except Exception as e:
            print(f"✗ Ошибка при создании таблицы telegram_headlines: {str(e)}")
        
        print(f"\n✓ Создано Telegram таблиц: {created_count}")
        
    finally:
        client.close()


def create_universal_tables():
    """Создает универсальные таблицы для объединенных данных"""
    client = get_clickhouse_client()
    
    try:
        print("\n" + "=" * 60)
        print("ШАГ 4: СОЗДАНИЕ УНИВЕРСАЛЬНЫХ ТАБЛИЦ")
        print("=" * 60)
        
        categories = [
            'military_operations',
            'humanitarian_crisis',
            'economic_consequences',
            'political_decisions',
            'information_social',
            # Дополнительные категории
            'ukraine',
            'middle_east',
            'fake_news',
            'info_war',
            'europe',
            'usa',
            'other'
        ]
        
        created_count = 0
        
        for category in categories:
            table_name = f'universal_{category}'
            
            create_query = f"""
            CREATE TABLE IF NOT EXISTS news.{table_name} (
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String DEFAULT '',
                content String,
                source String,
                category String DEFAULT '{category}',
                published_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY published_date
            """
            
            try:
                client.query(create_query)
                print(f"✓ Создана таблица: {table_name}")
                created_count += 1
            except Exception as e:
                print(f"✗ Ошибка при создании таблицы {table_name}: {str(e)}")
        
        print(f"\n✓ Создано универсальных таблиц: {created_count}")
        
    finally:
        client.close()


def create_category_tables():
    """Создает категорийные таблицы для каждого источника"""
    client = get_clickhouse_client()
    
    try:
        print("\n" + "=" * 60)
        print("ШАГ 4.5: СОЗДАНИЕ КАТЕГОРИЙНЫХ ТАБЛИЦ")
        print("=" * 60)
        
        # Источники, которым нужны категорийные таблицы
        sources = ['lenta', 'rbc', 'gazeta', 'kommersant', 'tsn', 'unian', 'rt', 'cnn', 'bbc', 
                   'aljazeera', 'reuters', 'france24', 'dw', 'euronews', 'ria', 'israil']
        
        # Категории
        categories = [
            'military_operations',
            'humanitarian_crisis',
            'economic_consequences',
            'political_decisions',
            'information_social',
            'ukraine',
            'middle_east',
            'fake_news',
            'info_war',
            'europe',
            'usa',
            'other'
        ]
        
        created_count = 0
        
        for source in sources:
            for category in categories:
                table_name = f'{source}_{category}'
                
                create_query = f"""
                CREATE TABLE IF NOT EXISTS news.{table_name} (
                    id UUID DEFAULT generateUUIDv4(),
                    title String,
                    link String,
                    content String,
                    rubric String DEFAULT '',
                    source String,
                    category String DEFAULT '{category}',
                    published_date DateTime DEFAULT now()
                ) ENGINE = MergeTree()
                ORDER BY published_date
                """
                
                try:
                    client.query(create_query)
                    created_count += 1
                except Exception as e:
                    print(f"✗ Ошибка при создании таблицы {table_name}: {str(e)}")
        
        print(f"✓ Создано категорийных таблиц: {created_count} ({len(sources)} источников × {len(categories)} категорий)")
        
    finally:
        client.close()


def create_analytics_tables():
    """Создает аналитические таблицы"""
    client = get_clickhouse_client()
    
    try:
        print("\n" + "=" * 60)
        print("ШАГ 5: СОЗДАНИЕ АНАЛИТИЧЕСКИХ ТАБЛИЦ")
        print("=" * 60)
        
        created_count = 0
        
        # Таблицы для аналитики социальных сетей
        analytics_tables = [
            """
            CREATE TABLE IF NOT EXISTS news.telegram_channels_stats (
                channel String,
                total_messages Int64 DEFAULT 0,
                avg_extremism Float64 DEFAULT 0,
                high_risk_count Int64 DEFAULT 0,
                last_updated DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY channel
            """,
            """
            CREATE TABLE IF NOT EXISTS news.telegram_classification_analytics (
                id UUID DEFAULT generateUUIDv4(),
                channel String,
                message_date DateTime,
                extremism_score Float64,
                risk_level String,
                keywords Array(String)
            ) ENGINE = MergeTree()
            ORDER BY message_date
            """,
            """
            CREATE TABLE IF NOT EXISTS news.social_media_extremism_analysis (
                id UUID DEFAULT generateUUIDv4(),
                platform String,
                content String,
                author String,
                extremism_percentage Float64,
                risk_level String,
                analysis_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY analysis_date
            """,
            """
            CREATE TABLE IF NOT EXISTS news.news_sources_extremism_analysis (
                id UUID DEFAULT generateUUIDv4(),
                source String,
                title String,
                content String,
                extremism_percentage Float64,
                risk_level String,
                analysis_date DateTime DEFAULT now()
            ) ENGINE = MergeTree()
            ORDER BY analysis_date
            """
        ]
        
        for query in analytics_tables:
            try:
                client.query(query)
                # Извлекаем имя таблицы из запроса
                table_name = query.split('news.')[1].split(' ')[0]
                print(f"✓ Создана таблица: {table_name}")
                created_count += 1
            except Exception as e:
                print(f"✗ Ошибка при создании аналитической таблицы: {str(e)}")
        
        print(f"\n✓ Создано аналитических таблиц: {created_count}")
        
    finally:
        client.close()


def create_social_media_tables():
    """Создает таблицы для социальных сетей"""
    client = get_clickhouse_client()
    
    try:
        print("\n" + "=" * 60)
        print("ШАГ 6: СОЗДАНИЕ ТАБЛИЦ СОЦИАЛЬНЫХ СЕТЕЙ")
        print("=" * 60)
        
        created_count = 0
        
        # Twitter
        twitter_query = """
        CREATE TABLE IF NOT EXISTS news.twitter_posts (
            id String,
            text String,
            author_username String,
            author_name String,
            created_at DateTime,
            public_metrics_like_count Int64 DEFAULT 0,
            public_metrics_retweet_count Int64 DEFAULT 0,
            public_metrics_reply_count Int64 DEFAULT 0,
            extremism_percentage Float64 DEFAULT 0,
            risk_level String DEFAULT 'Низкий',
            platform String DEFAULT 'Twitter'
        ) ENGINE = MergeTree()
        ORDER BY created_at
        """
        
        try:
            client.query(twitter_query)
            print(f"✓ Создана таблица: twitter_posts")
            created_count += 1
        except Exception as e:
            print(f"✗ Ошибка при создании таблицы twitter_posts: {str(e)}")
        
        # VK
        vk_query = """
        CREATE TABLE IF NOT EXISTS news.vk_posts (
            id String,
            text String,
            from_id String,
            date DateTime,
            likes_count Int64 DEFAULT 0,
            reposts_count Int64 DEFAULT 0,
            views_count Int64 DEFAULT 0,
            extremism_percentage Float64 DEFAULT 0,
            risk_level String DEFAULT 'Низкий',
            platform String DEFAULT 'VK'
        ) ENGINE = MergeTree()
        ORDER BY date
        """
        
        try:
            client.query(vk_query)
            print(f"✓ Создана таблица: vk_posts")
            created_count += 1
        except Exception as e:
            print(f"✗ Ошибка при создании таблицы vk_posts: {str(e)}")
        
        # OK (Одноклассники)
        ok_query = """
        CREATE TABLE IF NOT EXISTS news.ok_posts (
            id String,
            text String,
            author_name String,
            created_time DateTime,
            likes_count Int64 DEFAULT 0,
            extremism_percentage Float64 DEFAULT 0,
            risk_level String DEFAULT 'Низкий',
            platform String DEFAULT 'OK'
        ) ENGINE = MergeTree()
        ORDER BY created_time
        """
        
        try:
            client.query(ok_query)
            print(f"✓ Создана таблица: ok_posts")
            created_count += 1
        except Exception as e:
            print(f"✗ Ошибка при создании таблицы ok_posts: {str(e)}")
        
        print(f"\n✓ Создано таблиц социальных сетей: {created_count}")
        
    finally:
        client.close()


def reset_database():
    """Полный сброс и пересоздание базы данных"""
    print("\n" + "=" * 60)
    print("СБРОС И ПЕРЕСОЗДАНИЕ БАЗЫ ДАННЫХ CLICKHOUSE")
    print("=" * 60)
    
    # Удаляем все таблицы
    drop_all_tables()
    
    # Создаем новые таблицы
    create_news_tables()
    create_telegram_tables()
    create_universal_tables()
    create_category_tables()  # Новый шаг - категорийные таблицы
    create_analytics_tables()
    create_social_media_tables()
    
    print("\n" + "=" * 60)
    print("✓ БАЗА ДАННЫХ УСПЕШНО ПЕРЕСОЗДАНА!")
    print("=" * 60)
    print("\nТеперь вы можете запустить парсеры для заполнения данных.")
    print("Используйте веб-интерфейс (страница 'База данных')")
    print("или запустите парсеры вручную из папки 'parsers/'")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    # Запрашиваем подтверждение
    print("\n⚠️  ВНИМАНИЕ! ⚠️")
    print("Этот скрипт удалит ВСЕ таблицы и данные из базы данных ClickHouse!")
    print("И создаст новые пустые таблицы для проекта.")
    print("Это действие НЕОБРАТИМО!\n")
    
    response = input("Вы уверены, что хотите продолжить? (введите 'ДА' для подтверждения): ")
    
    if response.strip().upper() == 'ДА':
        reset_database()
    else:
        print("\n✓ Операция отменена")
        sys.exit(0)

