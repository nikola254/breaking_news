import sys
import os
from clickhouse_driver import Client
from datetime import datetime, timedelta
import pandas as pd
import re
import random
import socket
import time

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config

def connect_to_clickhouse(max_retries=3, retry_delay=2):
    """Establish connection to ClickHouse database with retry mechanism"""
    # Increase socket buffer size to handle the connection
    socket.setdefaulttimeout(30)  # Increase socket timeout
    
    for attempt in range(max_retries):
        try:
            # Try with explicit settings to avoid buffer issues
            client = Client(
                host=Config.CLICKHOUSE_HOST, 
                port=Config.CLICKHOUSE_NATIVE_PORT,
                user=Config.CLICKHOUSE_USER,
                password=Config.CLICKHOUSE_PASSWORD,
                settings={
                    'max_block_size': 100000,
                    'connect_timeout': 10,
                    'receive_timeout': 300,
                    'send_timeout': 300
                }
            )
            # Test connection with a simple query
            client.execute('SELECT 1')
            return client
        except Exception as e:
            if "буфер слишком мал или очередь переполнена" in str(e) or "buffer too small" in str(e):
                print(f"Socket buffer error on attempt {attempt+1}/{max_retries}. Trying to adjust...")
                # Wait before retrying
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
            else:
                print(f"Error connecting to ClickHouse: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("\nTROUBLESHOOTING TIPS:")
                    print("1. Make sure ClickHouse is running. Check with 'docker ps'")
                    print("2. Try restarting the ClickHouse container:")
                    print("   docker restart breaking_news-clickhouse-1")
                    print("3. Windows socket buffer issue may require system restart")
                    print("4. As a workaround, you can use sample data instead")
                    
                    use_sample = input("\nUse sample data instead? (y/n): ").lower()
                    if use_sample == 'y':
                        return None
                    sys.exit(1)
    
    return None

def get_recent_headlines(client, days=7, limit=50):
    """Retrieve recent headlines from both sources"""
    
    # If client is None, return sample data
    if client is None:
        return get_sample_headlines()
    
    # Get date for filtering
    cutoff_date = datetime.now() - timedelta(days=days)
    formatted_date = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
    
    # Query for RIA headlines
    ria_query = f"""
    SELECT title, link, source, category, parsed_date
    FROM news.ria_headlines
    WHERE parsed_date >= '{formatted_date}'
    ORDER BY parsed_date DESC
    LIMIT {limit}
    """
    
    # Query for Israel headlines
    israil_query = f"""
    SELECT title, link, source, category, parsed_date
    FROM news.israil_headlines
    WHERE parsed_date >= '{formatted_date}'
    ORDER BY parsed_date DESC
    LIMIT {limit}
    """
    
    try:
        # Execute queries
        ria_headlines = client.execute(ria_query)
        israil_headlines = client.execute(israil_query)
        
        # Convert to pandas DataFrames
        ria_df = pd.DataFrame(ria_headlines, 
                             columns=['title', 'link', 'source', 'category', 'parsed_date'])
        israil_df = pd.DataFrame(israil_headlines, 
                                columns=['title', 'link', 'source', 'category', 'parsed_date'])
        
        # Combine results
        all_headlines = pd.concat([ria_df, israil_df])
        
        # Sort by date (most recent first)
        all_headlines = all_headlines.sort_values('parsed_date', ascending=False)
        
        return all_headlines
    except Exception as e:
        print(f"Error querying ClickHouse: {e}")
        print("Falling back to sample data...")
        return get_sample_headlines()

def get_sample_headlines():
    """Return sample headlines when database is unavailable"""
    sample_data = [
        {
            'title': 'Израиль нанес удары по целям в Ливане',
            'link': 'https://example.com/news1',
            'source': 'ria.ru',
            'category': 'world',
            'parsed_date': datetime.now() - timedelta(hours=5)
        },
        {
            'title': 'США выделили новый пакет военной помощи Украине',
            'link': 'https://example.com/news2',
            'source': 'ria.ru',
            'category': 'world',
            'parsed_date': datetime.now() - timedelta(hours=8)
        },
        {
            'title': 'Переговоры о прекращении огня в секторе Газа продолжаются',
            'link': 'https://example.com/news3',
            'source': '7kanal.co.il',
            'category': 'section32',
            'parsed_date': datetime.now() - timedelta(hours=3)
        },
        {
            'title': 'Экономический форум в Давосе обсудил глобальные вызовы',
            'link': 'https://example.com/news4',
            'source': 'ria.ru',
            'category': 'world',
            'parsed_date': datetime.now() - timedelta(hours=12)
        },
        {
            'title': 'Новые санкции против России вступили в силу',
            'link': 'https://example.com/news5',
            'source': 'ria.ru',
            'category': 'world',
            'parsed_date': datetime.now() - timedelta(hours=10)
        }
    ]
    
    return pd.DataFrame(sample_data)

def clean_headline(headline):
    """Clean and normalize headline text"""
    # Remove special characters and extra spaces
    cleaned = re.sub(r'[^\w\s]', ' ', headline)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def generate_forecast_prompt(headlines_df, num_headlines=10, topic=None):
    """Generate a prompt for the neural network based on recent headlines"""
    
    # Filter by topic if specified
    if topic:
        topic_pattern = re.compile(topic, re.IGNORECASE)
        filtered_headlines = headlines_df[headlines_df['title'].apply(
            lambda x: bool(topic_pattern.search(x)))]
    else:
        filtered_headlines = headlines_df
    
    # If no headlines match the topic, use all headlines
    if filtered_headlines.empty:
        filtered_headlines = headlines_df
    
    # Select random headlines if we have more than needed
    if len(filtered_headlines) > num_headlines:
        selected_headlines = filtered_headlines.sample(num_headlines)
    else:
        selected_headlines = filtered_headlines
    
    # Clean headlines
    cleaned_headlines = [clean_headline(h) for h in selected_headlines['title']]
    
    # Format the prompt
    headline_list = "\n".join([f"- {h}" for h in cleaned_headlines])
    
    prompt = f"""Based on the following recent news headlines:

{headline_list}

Analyze these headlines and provide:
1. A summary of the current situation
2. Potential short-term developments (next 1-2 weeks)
3. Possible medium-term implications (1-3 months)
4. Key factors to watch that might influence how events unfold

Your analysis should be factual, balanced, and consider multiple perspectives.
"""
    
    return prompt

def get_topic_specific_forecast(topic, days=7, num_headlines=10):
    """Generate a forecast prompt for a specific topic"""
    client = connect_to_clickhouse()
    headlines = get_recent_headlines(client, days=days)
    prompt = generate_forecast_prompt(headlines, num_headlines=num_headlines, topic=topic)
    return prompt

def get_general_forecast(days=7, num_headlines=15):
    """Generate a general forecast prompt"""
    client = connect_to_clickhouse()
    headlines = get_recent_headlines(client, days=days)
    prompt = generate_forecast_prompt(headlines, num_headlines=num_headlines)
    return prompt

def get_source_specific_forecast(source, days=7, num_headlines=10):
    """Generate a forecast prompt for a specific news source"""
    client = connect_to_clickhouse()
    headlines = get_recent_headlines(client, days=days)
    
    # Filter by source
    filtered_headlines = headlines[headlines['source'].str.contains(source, case=False)]
    
    # If no headlines match the source, use all headlines
    if filtered_headlines.empty:
        filtered_headlines = headlines
    
    prompt = generate_forecast_prompt(filtered_headlines, num_headlines=num_headlines)
    return prompt

if __name__ == "__main__":
    # Example usage
    print("1. General forecast")
    print("2. Topic-specific forecast")
    print("3. Source-specific forecast")
    choice = input("Select an option (1-3): ")
    
    if choice == "1":
        days = int(input("How many days of news to consider? (default: 7): ") or 7)
        num_headlines = int(input("How many headlines to include? (default: 15): ") or 15)
        prompt = get_general_forecast(days=days, num_headlines=num_headlines)
        
    elif choice == "2":
        topic = input("Enter a topic (e.g., 'Ukraine', 'economy', 'Israel'): ")
        days = int(input("How many days of news to consider? (default: 7): ") or 7)
        num_headlines = int(input("How many headlines to include? (default: 10): ") or 10)
        prompt = get_topic_specific_forecast(topic, days=days, num_headlines=num_headlines)
        
    elif choice == "3":
        source = input("Enter a source (e.g., 'ria', '7kanal'): ")
        days = int(input("How many days of news to consider? (default: 7): ") or 7)
        num_headlines = int(input("How many headlines to include? (default: 10): ") or 10)
        prompt = get_source_specific_forecast(source, days=days, num_headlines=num_headlines)
        
    else:
        print("Invalid choice. Using general forecast.")
        prompt = get_general_forecast()
    
    print("\n" + "="*50 + "\n")
    print("GENERATED PROMPT FOR AI MODEL:")
    print("\n" + "="*50 + "\n")
    print(prompt)
    print("\n" + "="*50)