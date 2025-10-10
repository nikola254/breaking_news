from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from clickhouse_driver import Client
from datetime import datetime, timedelta
import re
import time
import logging
import sys
import os

# Добавляем путь к парсерам для импорта модулей
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))

from parsers.gen_api_classifier import GenApiNewsClassifier
from parsers.news_categories import classify_news, create_category_tables
from parsers.ukraine_relevance_filter import filter_ukraine_relevance

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("israil_parser.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_ukraine_tables_if_not_exists():
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Create database if not exists
    client.execute('CREATE DATABASE IF NOT EXISTS news')
    
    # Create table if not exists - adding content and sources fields
    client.execute('''
        CREATE TABLE IF NOT EXISTS news.israil_headlines (
            id UUID DEFAULT generateUUIDv4(),
            title String,
            link String,
            content String,
            source_links String,
            source String DEFAULT '7kanal.co.il',
            category String DEFAULT 'section32',
            published_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (published_date, id)
    ''')
    
    # Создаем таблицы для каждой категории
    create_category_tables(client)

def setup_webdriver():
    """Create and configure a WebDriver instance"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-logging')
    options.add_argument('--log-level=3')
    options.add_argument('--silent')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)  # Set page load timeout to 30 seconds
    return driver

def get_page_content(driver, url, wait_for_class=None, timeout=20):
    """Get the HTML content of a page using the provided WebDriver"""
    try:
        driver.get(url)
        
        if wait_for_class:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, wait_for_class))
            )
        
        return driver.page_source
    except Exception as e:
        logger.error(f"Error getting page content: {e}")
        return None

def parse_israil_news(driver=None):
    """Parse news from 7kanal.co.il"""
    create_driver = driver is None
    
    if create_driver:
        driver = setup_webdriver()
    
    try:
        url = "https://www.7kanal.co.il/section/32"
        logger.info(f"Fetching news from {url}")
        
        html = get_page_content(driver, url, wait_for_class="category-container")
        if not html:
            logger.error("Failed to get page content")
            return 0
            
        soup = BeautifulSoup(html, "html.parser")
        
        # Connect to ClickHouse
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        
        # Get existing links to avoid duplicates
        existing_links = set()
        try:
            result = client.execute('SELECT DISTINCT link FROM news.israil_headlines')
            existing_links = {row[0] for row in result}
            logger.info(f"Found {len(existing_links)} existing articles")
        except Exception as e:
            logger.warning(f"Could not fetch existing links: {e}")
        
        headlines_data = []
        skipped_count = 0
        
        # Find all article links
        articles = soup.find_all('article', class_='category-item')
        logger.info(f"Found {len(articles)} articles")
        
        for article in articles:
            try:
                # Extract title and link
                title_element = article.find('h2')
                if not title_element:
                    continue
                    
                link_element = title_element.find('a')
                if not link_element:
                    continue
                    
                title = title_element.get_text(strip=True)
                link = link_element.get('href')
                
                if not link.startswith('http'):
                    link = 'https://www.7kanal.co.il' + link
                
                # Skip if already exists
                if link in existing_links:
                    skipped_count += 1
                    continue
                
                logger.info(f"Processing: {title}")
                
                # Get article content
                content = ""
                source_links = []
                
                try:
                    article_html = get_page_content(driver, link)
                    if article_html:
                        article_soup = BeautifulSoup(article_html, 'html.parser')
                        
                        # Extract content
                        content_div = article_soup.find('div', class_='article-content')
                        if content_div:
                            paragraphs = content_div.find_all('p')
                            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
                        
                        # Extract source links
                        source_link_elements = article_soup.find_all('a', href=True)
                        for link_elem in source_link_elements:
                            href = link_elem.get('href')
                            if href and ('http' in href) and ('7kanal.co.il' not in href):
                                source_links.append(href)
                
                except Exception as e:
                    logger.warning(f"Could not extract content for {link}: {e}")
                
                source_links_str = ', '.join(source_links[:5])  # Limit to 5 links
                
                # Проверяем релевантность к украинскому конфликту
                logger.info("Проверка релевантности к украинскому конфликту...")
                relevance_result = filter_ukraine_relevance(title, content)
                
                if not relevance_result['is_relevant']:
                    logger.info(f"Статья не релевантна украинскому конфликту (score: {relevance_result['relevance_score']:.2f})")
                    continue
                
                logger.info(f"Статья релевантна (score: {relevance_result['relevance_score']:.2f}, категория: {relevance_result['category']})")
                logger.info(f"Найденные ключевые слова: {relevance_result['keywords_found']}")
                
                # Используем категорию из фильтра релевантности
                category = relevance_result.get('category', 'other')

                if not category or category is None:
                    category = 'other'
                logger.info(f"Категория: {category}")
                
                # Пропускаем статьи с категорией 'other' - они не нужны в БД
                if category == 'other':
                    logger.info(f"Пропущено (категория 'other'): {title[:50]}...")
                    continue
                
                # Add to data for insertion
                headlines_data.append({
                    'title': title,
                    'link': link,
                    'content': content,
                    'source_links': source_links_str,
                    'category': category,
                    'published_date': datetime.now()
                })
                
            except Exception as e:
                logger.error(f"Error processing article: {e}")
                continue
        
        # Insert data into ClickHouse
        if headlines_data:
            # Вставляем в общую таблицу
            client.execute(
                'INSERT INTO news.israil_headlines (title, link, content, source_links, category, published_date) VALUES',
                headlines_data
            )
            
            # Группируем данные по категориям
            categorized_data = {}
            for item in headlines_data:
                category = item['category']
                if category not in categorized_data:
                    categorized_data[category] = []
                categorized_data[category].append(item)
            
            # Вставляем данные в соответствующие таблицы категорий
            for category, data in categorized_data.items():
                if data:
                    client.execute(
                        f'INSERT INTO news.israil_{category} (title, link, content, source_links, category, published_date) VALUES',
                        data
                    )
            
            logger.info(f"Added {len(headlines_data)} articles to database")
            # Выводим статистику по категориям
            for category, data in categorized_data.items():
                logger.info(f"Категория {category}: {len(data)} статей")
        else:
            logger.info("No new articles to add")
        
        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} duplicates")
            
        return len(headlines_data)
    
    except Exception as e:
        logger.error(f"Error in parse_israil_news: {e}")
        return 0
    
    finally:
        if create_driver and driver:
            driver.quit()

def continuous_monitoring(interval_minutes=15):
    """Continuously monitor for new articles"""
    logger.info(f"Starting continuous monitoring. Checking every {interval_minutes} minutes")
    
    # Create table if it doesn't exist
    create_ukraine_tables_if_not_exists()
    
    # Create a single WebDriver instance to reuse
    driver = setup_webdriver()
    
    try:
        while True:
            logger.info(f"Checking for new articles at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            new_articles = parse_israil_news(driver)
            
            if new_articles > 0:
                logger.info(f"Found {new_articles} new articles")
            else:
                logger.info("No new articles found")
                
            # Calculate next check time
            next_check = datetime.now() + timedelta(minutes=interval_minutes)
            logger.info(f"Next check at {next_check.strftime('%H:%M:%S')}")
            
            # Sleep until next check
            time.sleep(interval_minutes * 60)
    
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Error in monitoring: {e}")
    finally:
        if driver:
            driver.quit()

# Add this function after extract_article_content function
def test_clickhouse_connection():
    """Test connection to ClickHouse and verify table exists"""
    try:
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        
        # Test basic connection
        result = client.execute('SELECT 1')
        logger.info(f"ClickHouse connection test: {result}")
        
        # Check if our table exists
        tables = client.execute("SHOW TABLES FROM news")
        logger.info(f"Tables in 'news' database: {tables}")
        
        # Check record count
        if any(table[0] == 'israil_headlines' for table in tables):
            count = client.execute("SELECT COUNT(*) FROM news.israil_headlines")[0][0]
            logger.info(f"Current record count in israil_headlines: {count}")
        
        return True
    except Exception as e:
        logger.error(f"ClickHouse connection error: {e}")
        return False

# Modify the main section to include the test
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Parse news from 7kanal.co.il')
    parser.add_argument('--monitor', action='store_true', help='Run in continuous monitoring mode')
    parser.add_argument('--interval', type=int, default=15, help='Check interval in minutes (default: 15)')
    parser.add_argument('--test', action='store_true', help='Test ClickHouse connection')
    parser.add_argument('--view', action='store_true', help='View data from database')
    parser.add_argument('--limit', type=int, default=10, help='Limit number of records to view')
    parser.add_argument('--fix-duplicates', action='store_true', help='Fix duplicate entries in database')
    
    args = parser.parse_args()
    
    if args.test:
        logger.info("Testing ClickHouse connection...")
        test_clickhouse_connection()
        exit(0)
    
    if args.view:
        logger.info("Viewing database data...")
        view_database_data(limit=args.limit)
        exit(0)
    
    if args.fix_duplicates:
        logger.info("Fixing duplicate entries...")
        # Add code to fix duplicates
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        
        # Find duplicates
        duplicates = client.execute("""
            SELECT 
                link,
                count(*) as count,
                groupArray(id) as ids
            FROM news.israil_headlines
            GROUP BY link
            HAVING count > 1
        """)
        
        if duplicates:
            logger.info(f"Found {len(duplicates)} links with duplicates")
            
            for link, count, ids in duplicates:
                # Keep the first entry (usually the one with data)
                keep_id = ids[0]
                delete_ids = ids[1:]
                
                # Delete duplicates
                for delete_id in delete_ids:
                    client.execute(f"ALTER TABLE news.israil_headlines DELETE WHERE id = '{delete_id}'")
                
                logger.info(f"Kept ID {keep_id} and deleted {len(delete_ids)} duplicates for link: {link}")
            
            logger.info("Duplicate cleanup completed")
        else:
            logger.info("No duplicates found")
        
        exit(0)
    
    # Always test connection before starting
    if not test_clickhouse_connection():
        logger.error("Failed to connect to ClickHouse. Exiting.")
        exit(1)
    
    if args.monitor:
        continuous_monitoring(args.interval)
    else:
        # Run once
        create_ukraine_tables_if_not_exists()
        parse_israil_news()
