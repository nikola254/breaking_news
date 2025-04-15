from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from clickhouse_driver import Client
from datetime import datetime

def create_table_if_not_exists():
    client = Client(host='localhost', port=9000)
    
    # Create database if not exists
    client.execute('CREATE DATABASE IF NOT EXISTS news')
    
    # Create table if not exists
    client.execute('''
        CREATE TABLE IF NOT EXISTS news.israil_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String,
            source String DEFAULT '7kanal.co.il',
            category String DEFAULT 'section32',
            parsed_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (parsed_date, id)
    ''')

def get_dynamic_page(url):
    # Настраиваем Chrome для работы в режиме headless
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    
    # Создаём экземпляр драйвера (убедитесь, что у вас установлен ChromeDriver и он доступен)
    driver = webdriver.Chrome(options=options)
    
    # Загружаем страницу
    driver.get(url)
    
    try:
        # Ожидаем появления элемента с классом "category-container" (например, до 10 секунд)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "category-container"))
        )
    except Exception as e:
        print("Элемент не найден или произошла ошибка ожидания:", e)
    
    # Получаем отрендеренный HTML-код страницы
    rendered_html = driver.page_source
    driver.quit()
    return rendered_html

if __name__ == "__main__":
    # Create table in ClickHouse if it doesn't exist
    create_table_if_not_exists()
    
    url = "https://www.7kanal.co.il/section/32"
    html = get_dynamic_page(url)
    soup = BeautifulSoup(html, "html.parser")
    
    # Connect to ClickHouse
    client = Client(host='localhost', port=9000)
    
    # Get existing links to avoid duplicates
    existing_links = set(row[0] for row in client.execute('SELECT link FROM news.israil_headlines'))
    
    # Prepare data for batch insert
    headlines_data = []
    skipped_count = 0
    
    # Ищем контейнер <div> с классом "category-container"
    container = soup.find("div", class_="category-container")
    if container:
        print("Контейнер найден!")
        # Здесь можно продолжить извлечение контента, например, искать внутри container тег <section> или конкретные ссылки
        # Например:
        section = container.find("section")
        if section:
            articles = section.find_all("a", class_="article article-sub-pages category-article")
            for article in articles:
                title_tag = article.find("h2", class_="article-content--title")
                title = title_tag.get_text(strip=True) if title_tag else article.get_text(strip=True)
                link = article.get("href")
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
        print("Контейнер с классом 'category-container' не найден")
    
    # Insert data into ClickHouse if we have any
    if headlines_data:
        client.execute(
            'INSERT INTO news.israil_headlines (title, link, parsed_date) VALUES',
            headlines_data
        )
        print(f"Добавлено {len(headlines_data)} записей в базу данных")
    
    if skipped_count > 0:
        print(f"Пропущено {skipped_count} дубликатов")
