import requests
from bs4 import BeautifulSoup
from clickhouse_driver import Client
from datetime import datetime


def create_table_if_not_exists():
    client = Client(host='localhost', port=9000)
    
    # Create database if not exists
    client.execute('CREATE DATABASE IF NOT EXISTS news')
    
    # Create table if not exists
    client.execute('''
        CREATE TABLE IF NOT EXISTS news.ria_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String,
            source String DEFAULT 'ria.ru',
            category String DEFAULT 'world',
            parsed_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (parsed_date, id)
    ''')


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

    for article in articles:
        # Ищем тег <a> с нужным классом внутри контейнера
        link_tag = article.find("a", class_="list-item__title color-font-hover-only")
        if link_tag:
            title = link_tag.get_text(strip=True)
            link = link_tag.get("href")
            print("Заголовок:", title)
            print("Ссылка:", link)
            print("-" * 40)
            
            # Check if this link already exists in the database
            if link in existing_links:
                print(f"Пропуск дубликата: {title}")
                skipped_count += 1
                continue
                
            # Add to data for insertion
            headlines_data.append({
                'title': title,
                'link': link,
                'parsed_date': datetime.now()
            })
        else:
            print("В контейнере не найден тег <a> с классом 'list-item__title color-font-hover-only'.")
    
    # Insert data into ClickHouse if we have any
    if headlines_data:
        client.execute(
            'INSERT INTO news.ria_headlines (title, link, parsed_date) VALUES',
            headlines_data
        )
        print(f"Добавлено {len(headlines_data)} записей в базу данных")
    
    if skipped_count > 0:
        print(f"Пропущено {skipped_count} дубликатов")


if __name__ == "__main__":
    create_table_if_not_exists()
    parse_politics_headlines()
