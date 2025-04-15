import requests
from bs4 import BeautifulSoup
from clickhouse_driver import Client
from datetime import datetime
import time
import random


def create_table_if_not_exists():
    client = Client(host='localhost', port=9000)
    
    # Create database if not exists
    client.execute('CREATE DATABASE IF NOT EXISTS news')
    
    # Create table if not exists - adding content field
    client.execute('''
        CREATE TABLE IF NOT EXISTS news.ria_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String,
            content String,
            source String DEFAULT 'ria.ru',
            category String DEFAULT 'world',
            parsed_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (parsed_date, id)
    ''')


def get_article_content(url, headers):
    """Extract full content of an article"""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find the article content - adjust selectors based on RIA's HTML structure
        article_body = soup.find("div", class_="article__body")
        
        if not article_body:
            return "Не удалось извлечь содержимое статьи"
        
        # Extract paragraphs
        paragraphs = article_body.find_all("div", class_="article__text")
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        
        return content
    except Exception as e:
        print(f"Ошибка при получении содержимого статьи {url}: {e}")
        return "Ошибка при получении содержимого статьи"


def parse_politics_headlines():
    url = "https://ria.ru/world/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Проверка успешного запроса
    except requests.RequestException as e:
        print("Ошибка при получении данных:", e)
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # Замените 'YOUR_DIV_CLASS_NAME' на актуальное название класса для контейнера статьи
    articles = soup.find_all("div", class_="list-item__content")
    
    if not articles:
        print("Не найдено ни одного контейнера с указанным классом")
        return

    # Connect to ClickHouse
    client = Client(host='localhost', port=9000)
    
    # Get existing links to avoid duplicates
    existing_links = set(row[0] for row in client.execute('SELECT link FROM news.ria_headlines'))
    
    # Prepare data for batch insert
    headlines_data = []
    skipped_count = 0
    new_count = 0

    for article in articles:
        # Ищем тег <a> с нужным классом внутри контейнера
        link_tag = article.find("a", class_="list-item__title color-font-hover-only")
        if link_tag:
            title = link_tag.get_text(strip=True)
            link = link_tag.get("href")
            
            # Check if this link already exists in the database
            if link in existing_links:
                skipped_count += 1
                continue
                
            print("Найдена новая статья:")
            print("Заголовок:", title)
            print("Ссылка:", link)
            
            # Get full article content
            print("Получение содержимого статьи...")
            content = get_article_content(link, headers)
            print(f"Получено {len(content)} символов содержимого")
            print("-" * 40)
            
            # Add to data for insertion
            headlines_data.append({
                'title': title,
                'link': link,
                'content': content,
                'parsed_date': datetime.now()
            })
            
            new_count += 1
            
            # Add a small delay between article requests to avoid overloading the server
            time.sleep(random.uniform(1, 3))
        else:
            print("В контейнере не найден тег <a> с классом 'list-item__title color-font-hover-only'.")
    
    # Insert data into ClickHouse if we have any
    if headlines_data:
        client.execute(
            'INSERT INTO news.ria_headlines (title, link, content, parsed_date) VALUES',
            headlines_data
        )
        print(f"Добавлено {len(headlines_data)} записей в базу данных")
    
    if skipped_count > 0:
        print(f"Пропущено {skipped_count} дубликатов")
        
    return new_count


def continuous_monitoring(interval_minutes=5):
    """Continuously monitor for new articles"""
    print(f"Запуск непрерывного мониторинга новостей RIA. Интервал проверки: {interval_minutes} минут")
    
    try:
        # Create table if it doesn't exist
        create_table_if_not_exists()
        
        while True:
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Проверка новых статей...")
            new_articles = parse_politics_headlines()
            
            if new_articles:
                print(f"Найдено {new_articles} новых статей")
            else:
                print("Новых статей не найдено")
                
            # Wait for the next check
            next_check = datetime.now() + timedelta(minutes=interval_minutes)
            print(f"Следующая проверка в {next_check.strftime('%H:%M:%S')}")
            time.sleep(interval_minutes * 60)
    
    except KeyboardInterrupt:
        print("\nМониторинг остановлен пользователем")
    except Exception as e:
        print(f"Ошибка в процессе мониторинга: {e}")
        # Wait a bit and restart monitoring
        print("Перезапуск мониторинга через 1 минуту...")
        time.sleep(60)
        continuous_monitoring(interval_minutes)


if __name__ == "__main__":
    from datetime import timedelta
    continuous_monitoring()
