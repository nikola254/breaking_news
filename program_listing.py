# ЛИСТИНГ ПРОГРАММЫ ДЛЯ РЕГИСТРАЦИИ ЭВМ
# Система парсинга новостей с использованием различных технологий
# Демонстрация на примере двух парсеров: РИА Новости и Израиль Новости

# ============================================================================
# ЮНИТ 1: ЗАГРУЗКА БИБЛИОТЕК И ОТБОР ПАРАМЕТРОВ
# ============================================================================

# Импорт библиотек для парсера РИА Новости (технология BeautifulSoup + requests)
from bs4 import BeautifulSoup
import requests
from clickhouse_driver import Client
from datetime import datetime, timedelta
import time
import random
import sys
import os

# Импорт библиотек для парсера Израиль Новости (технология Selenium + WebDriver)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Общие библиотеки для работы с данными
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parsers'))
from parsers.news_categories import classify_news, create_category_tables

# Настройка логирования для парсера Израиль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("israil_parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Параметры для парсера РИА Новости
RIA_URL = "https://ria.ru/world/"
RIA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Параметры для парсера Израиль Новости
ISRAEL_URL = "https://www.7kanal.co.il/section/32"
ISRAEL_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

# ============================================================================
# ЮНИТ 2: ЗАГРУЗКА ДАННЫХ С САЙТА
# ============================================================================

# Функция загрузки данных для РИА Новости (статический парсинг)
def load_ria_data():
    """Загрузка данных с сайта РИА Новости используя requests + BeautifulSoup"""
    try:
        response = requests.get(RIA_URL, headers=RIA_HEADERS)
        response.raise_for_status()  # Проверка успешного запроса
        return response.content
    except requests.RequestException as e:
        print(f"Ошибка при получении данных РИА: {e}")
        return None

# Функция настройки WebDriver для Израиль Новости
def setup_webdriver():
    """Создание и настройка экземпляра WebDriver для динамического парсинга"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')
    options.add_argument('--silent')
    options.add_argument(f'--user-agent={ISRAEL_USER_AGENT}')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver

# Функция загрузки данных для Израиль Новости (динамический парсинг)
def load_israel_data(driver, wait_for_class=None, timeout=20):
    """Загрузка данных с сайта Израиль Новости используя Selenium WebDriver"""
    try:
        driver.get(ISRAEL_URL)
        
        # Ожидание загрузки основного контента
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Ожидание специфического элемента если указан
        if wait_for_class:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, wait_for_class))
                )
                logger.info(f"Найден элемент с классом '{wait_for_class}'")
            except:
                logger.warning(f"Элемент с классом '{wait_for_class}' не найден, продолжаем")
        
        # Пауза для выполнения JavaScript
        time.sleep(2)
        
        return driver.page_source
    except Exception as e:
        logger.error(f"Ошибка загрузки страницы {ISRAEL_URL}: {e}")
        return None

# Функция получения полного содержимого статьи РИА
def get_ria_article_content(url, headers):
    """Извлечение полного содержимого статьи РИА"""
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Поиск основного содержимого статьи
        article_body = soup.find("div", class_="article__body")
        
        if not article_body:
            return "Не удалось извлечь содержимое статьи"
        
        # Извлечение параграфов
        paragraphs = article_body.find_all("div", class_="article__text")
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
        
        return content
    except Exception as e:
        print(f"Ошибка при получении содержимого статьи {url}: {e}")
        return "Ошибка при получении содержимого статьи"

# ============================================================================
# ЮНИТ 3: ЗАГРУЗКА И СТРУКТУРИЗАЦИЯ ДАННЫХ
# ============================================================================

# Функция создания таблиц в ClickHouse
def create_database_tables():
    """Создание таблиц в базе данных ClickHouse"""
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Создание базы данных
    client.execute('CREATE DATABASE IF NOT EXISTS news')
    
    # Создание таблицы для РИА Новости
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
    
    # Создание таблицы для Израиль Новости
    client.execute('''
        CREATE TABLE IF NOT EXISTS news.israil_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String,
            content String,
            source_links String,
            source String DEFAULT '7kanal.co.il',
            category String DEFAULT 'section32',
            parsed_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (parsed_date, id)
    ''')
    
    # Создание таблиц для категорий
    create_category_tables(client)

# Функция парсинга и структуризации данных РИА
def parse_and_structure_ria_data():
    """Парсинг и структуризация данных РИА Новости"""
    # Загрузка данных
    content = load_ria_data()
    if not content:
        return 0
    
    soup = BeautifulSoup(content, "html.parser")
    
    # Поиск статей
    articles = soup.find_all("div", class_="list-item__content")
    
    if not articles:
        print("Не найдено статей РИА")
        return 0
    
    # Подключение к базе данных
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Получение существующих ссылок для избежания дубликатов
    existing_links = set(row[0] for row in client.execute('SELECT link FROM news.ria_headlines'))
    
    # Подготовка данных для вставки
    headlines_data = []
    new_count = 0
    
    for article in articles:
        # Извлечение заголовка и ссылки
        link_tag = article.find("a", class_="list-item__title color-font-hover-only")
        if link_tag:
            title = link_tag.get_text(strip=True)
            link = link_tag.get("href")
            
            # Проверка на дубликаты
            if link in existing_links:
                continue
            
            # Получение полного содержимого
            content = get_ria_article_content(link, RIA_HEADERS)
            
            # Классификация новости
            category = classify_news(title, content)
            
            # Добавление в данные для вставки
            headlines_data.append({
                'title': title,
                'link': link,
                'content': content,
                'category': category,
                'parsed_date': datetime.now()
            })
            
            new_count += 1
            
            # Пауза между запросами
            time.sleep(random.uniform(1, 3))
    
    # Вставка данных в базу
    if headlines_data:
        client.execute(
            'INSERT INTO news.ria_headlines (title, link, content, category, parsed_date) VALUES',
            headlines_data
        )
        
        # Группировка по категориям и вставка в соответствующие таблицы
        categorized_data = {}
        for item in headlines_data:
            category = item['category']
            if category not in categorized_data:
                categorized_data[category] = []
            categorized_data[category].append(item)
        
        for category, data in categorized_data.items():
            if data:
                client.execute(
                    f'INSERT INTO news.ria_{category} (title, link, content, category, parsed_date) VALUES',
                    data
                )
    
    return new_count

# Функция парсинга и структуризации данных Израиль
def parse_and_structure_israel_data():
    """Парсинг и структуризация данных Израиль Новости"""
    driver = setup_webdriver()
    
    try:
        # Загрузка данных
        html = load_israel_data(driver, wait_for_class="category-container")
        if not html:
            return 0
        
        soup = BeautifulSoup(html, "html.parser")
        
        # Подключение к базе данных
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        
        # Получение существующих ссылок
        existing_links = set(row[0] for row in client.execute('SELECT DISTINCT link FROM news.israil_headlines'))
        
        # Поиск статей
        articles = []
        container = soup.find("div", class_="category-container")
        if container:
            section = container.find("section")
            if section:
                articles = section.find_all("a", class_="article article-sub-pages category-article")
        
        if not articles:
            articles = soup.find_all("a", class_=lambda c: c and "article" in c)
        
        if not articles:
            logger.warning("Статьи Израиль не найдены")
            return 0
        
        # Подготовка данных
        headlines_data = []
        new_count = 0
        
        for article in articles:
            # Извлечение заголовка
            title_tag = article.find("h2")
            if not title_tag:
                title_tag = article.find(["h1", "h3", "h4", "div"], class_=lambda c: c and ("title" in c or "header" in c))
            
            title = title_tag.get_text(strip=True) if title_tag else article.get_text(strip=True)
            
            # Извлечение ссылки
            if article.name == "a":
                link = article.get("href")
            else:
                link_tag = article.find("a")
                link = link_tag.get("href") if link_tag else None
            
            if not link or link in existing_links:
                continue
            
            # Получение полного содержимого и источников
            try:
                article_html = load_israel_data(driver, link)
                if article_html:
                    article_soup = BeautifulSoup(article_html, "html.parser")
                    content, source_links = extract_article_content(article_soup)
                else:
                    content = "Не удалось загрузить содержимое"
                    source_links = []
            except:
                content = "Ошибка загрузки содержимого"
                source_links = []
            
            # Классификация
            category = classify_news(title, content)
            
            # Добавление данных
            headlines_data.append({
                'title': title,
                'link': link,
                'content': content,
                'source_links': ",".join(source_links),
                'category': category,
                'parsed_date': datetime.now()
            })
            
            new_count += 1
            time.sleep(2)  # Пауза между запросами
        
        # Вставка в базу данных
        if headlines_data:
            client.execute(
                'INSERT INTO news.israil_headlines (title, link, content, source_links, category, parsed_date) VALUES',
                headlines_data
            )
        
        return new_count
    
    finally:
        driver.quit()

# Функция извлечения содержимого статьи Израиль
def extract_article_content(soup):
    """Извлечение содержимого и ссылок источников из статьи Израиль"""
    # Поиск содержимого статьи
    content_selectors = [
        "div.article-content", 
        "div.article-body",
        "div.content",
        "article"
    ]
    
    content_element = None
    for selector in content_selectors:
        tag, class_name = selector.split(".")
        content_element = soup.find(tag, class_=class_name)
        if content_element:
            break
    
    if not content_element:
        return "Не удалось найти содержимое статьи", []
    
    # Извлечение параграфов
    paragraphs = content_element.find_all("p")
    if not paragraphs:
        content = content_element.get_text(strip=True)
    else:
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
    
    # Извлечение ссылок источников
    source_links = []
    links = content_element.find_all("a", href=True)
    for link in links:
        href = link.get("href")
        if href and not href.startswith("#") and "7kanal.co.il" not in href:
            if href.startswith("http"):
                source_links.append(href)
            else:
                source_links.append(f"https://www.7kanal.co.il{href}")
    
    return content, source_links

# Основная функция запуска парсинга
def main():
    """Основная функция для демонстрации работы парсеров"""
    print("=== ДЕМОНСТРАЦИЯ СИСТЕМЫ ПАРСИНГА НОВОСТЕЙ ===")
    print("Технологии: BeautifulSoup + requests (РИА) и Selenium + WebDriver (Израиль)")
    
    # Создание таблиц
    create_database_tables()
    
    # Парсинг РИА Новости
    print("\n--- Парсинг РИА Новости ---")
    ria_count = parse_and_structure_ria_data()
    print(f"Обработано статей РИА: {ria_count}")
    
    # Парсинг Израиль Новости
    print("\n--- Парсинг Израиль Новости ---")
    israel_count = parse_and_structure_israel_data()
    print(f"Обработано статей Израиль: {israel_count}")
    
    print(f"\nВсего обработано статей: {ria_count + israel_count}")

if __name__ == "__main__":
    main()

# КОНЕЦ ЛИСТИНГА ПРОГРАММЫ
# Данная программа демонстрирует использование двух различных технологий парсинга:
# 1. Статический парсинг (requests + BeautifulSoup) для сайтов без JavaScript
# 2. Динамический парсинг (Selenium + WebDriver) для сайтов с JavaScript
# Обе технологии интегрированы с системой классификации новостей и базой данных ClickHouse