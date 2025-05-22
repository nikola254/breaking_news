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
from news_categories import classify_news, create_category_tables

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

def create_table_if_not_exists():
    client = Client(host='localhost', port=9000)
    
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
            parsed_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (parsed_date, id)
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
        
        # Wait for the body to be present
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # If a specific class is provided, wait for it
        if wait_for_class:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, wait_for_class))
                )
                logger.info(f"Found element with class '{wait_for_class}'")
            except:
                logger.warning(f"Element with class '{wait_for_class}' not found, but continuing")
        
        # Short delay to ensure JavaScript execution
        time.sleep(2)
        
        return driver.page_source
    except Exception as e:
        logger.error(f"Error loading page {url}: {e}")
        return None

def extract_article_content(soup):
    """Extract content and source links from article soup"""
    # Try different selectors for article content
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
            logger.info(f"Found content using selector: {selector}")
            break
    
    if not content_element:
        logger.warning("Could not find article content with any selector")
        return "Не удалось найти содержимое статьи", []
    
    # Extract paragraphs
    paragraphs = content_element.find_all("p")
    if not paragraphs:
        # If no paragraphs found, try to get all text
        content = content_element.get_text(strip=True)
    else:
        content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
    
    # Extract source links
    source_links = []
    links = content_element.find_all("a", href=True)
    for link in links:
        href = link.get("href")
        # Check if link is external
        if href and not href.startswith("#") and not "7kanal.co.il" in href:
            if href.startswith("http"):
                source_links.append(href)
            else:
                # Handle relative URLs
                source_links.append(f"https://www.7kanal.co.il{href}")
    
    return content, source_links

# Add this function to view database data
def view_database_data(limit=None):
    """View data from the ClickHouse database to check for duplicates"""
    try:
        client = Client(host='localhost', port=9000)
        
        # Get total count
        count = client.execute("SELECT COUNT(*) FROM news.israil_headlines")[0][0]
        logger.info(f"Total records in database: {count}")
        
        # Query to find potential duplicates
        query = """
        SELECT 
            link,
            count(*) as count,
            groupArray(title) as titles,
            groupArray(id) as ids
        FROM news.israil_headlines
        GROUP BY link
        HAVING count > 1
        ORDER BY count DESC
        """
        
        duplicates = client.execute(query)
        
        if duplicates:
            logger.warning(f"Found {len(duplicates)} links with duplicates")
            print("\n=== DUPLICATE ENTRIES ===")
            for link, count, titles, ids in duplicates:
                print(f"\nLink: {link}")
                print(f"Count: {count}")
                print("Titles:")
                for i, title in enumerate(titles):
                    print(f"  {i+1}. ID: {ids[i]}, Title: {title[:100]}")
                print("-" * 80)
        else:
            logger.info("No duplicate links found")
        
        # Get sample data
        limit_clause = f"LIMIT {limit}" if limit is not None else ""
        sample_query = f"""
        SELECT 
            id,
            title,
            link,
            length(content) as content_length,
            parsed_date
        FROM news.israil_headlines
        ORDER BY parsed_date DESC
        {limit_clause}
        """
        
        results = client.execute(sample_query)
        
        print("\n=== SAMPLE DATA ===")
        for row in results:
            print(f"\nID: {row[0]}")
            print(f"Title: {row[1]}")
            print(f"Link: {row[2]}")
            print(f"Content Length: {row[3]}")
            print(f"Date: {row[4]}")
            print("-" * 80)
        
        return True
    except Exception as e:
        logger.error(f"Error querying database: {e}")
        return False

# Fix the duplicate checking in parse_israil_news function
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
        client = Client(host='localhost', port=9000)
        
        # Get existing links to avoid duplicates - use DISTINCT to ensure no duplicates
        existing_links = set(row[0] for row in client.execute('SELECT DISTINCT link FROM news.israil_headlines'))
        
        # Prepare data for batch insert
        headlines_data = []
        skipped_count = 0
        
        # Find articles using multiple methods
        articles = []
        
        # Method 1: Look for the container
        container = soup.find("div", class_="category-container")
        if container:
            logger.info("Found category container")
            section = container.find("section")
            if section:
                articles = section.find_all("a", class_="article article-sub-pages category-article")
        
        # Method 2: Alternative selectors if container not found or no articles
        if not articles:
            logger.info("Using alternative article selectors")
            articles = soup.find_all("a", class_=lambda c: c and "article" in c)
            
        if not articles:
            articles = soup.find_all("div", class_=lambda c: c and "article" in c)
        
        if not articles:
            logger.warning("No articles found with any method")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            logger.info("Saved HTML to debug_page.html")
            return 0
        
        logger.info(f"Found {len(articles)} articles")
        
        # Process articles
        for article in articles:
            # Extract title
            title_tag = article.find("h2")
            if not title_tag:
                title_tag = article.find(["h1", "h3", "h4", "div"], class_=lambda c: c and ("title" in c or "header" in c))
            
            title = title_tag.get_text(strip=True) if title_tag else article.get_text(strip=True)
            
            # Extract link
            if article.name == "a":
                link = article.get("href")
            else:
                link_tag = article.find("a")
                link = link_tag.get("href") if link_tag else None
            
            if not link:
                logger.info("Skipping article without link")
                continue
                
            # Handle relative URLs
            if link.startswith("/"):
                link = "https://www.7kanal.co.il" + link
                
            logger.info(f"Processing article: {title[:50]}...")
            
            # Skip duplicates
            if link in existing_links:
                logger.info(f"Skipping duplicate: {title[:50]}...")
                skipped_count += 1
                continue
            
            # Get article content
            article_html = get_page_content(driver, link, wait_for_class="article-content")
            if not article_html:
                logger.warning(f"Failed to get content for {link}")
                continue
                
            article_soup = BeautifulSoup(article_html, "html.parser")
            content, source_links = extract_article_content(article_soup)
            
            # Convert source links to string
            source_links_str = ", ".join(source_links) if source_links else ""
            
            logger.info(f"Content length: {len(content)} chars, Sources: {len(source_links)}")
            
            # Классифицируем новость по категориям
            category = classify_news(title, content)
            logger.info(f"Категория: {category}")
            
            # Add to data for insertion
            headlines_data.append({
                'title': title,
                'link': link,
                'content': content,
                'source_links': source_links_str,
                'category': category,
                'parsed_date': datetime.now()
            })
        
        # Insert data into ClickHouse
        if headlines_data:
            # Вставляем в общую таблицу
            client.execute(
                'INSERT INTO news.israil_headlines (title, link, content, source_links, category, parsed_date) VALUES',
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
                        f'INSERT INTO news.israil_{category} (title, link, content, source_links, category, parsed_date) VALUES',
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
    create_table_if_not_exists()
    
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
        client = Client(host='localhost', port=9000)
        
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
        client = Client(host='localhost', port=9000)
        
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
        create_table_if_not_exists()
        parse_israil_news()
