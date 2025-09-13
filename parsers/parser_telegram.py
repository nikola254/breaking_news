"""Парсер новостей из Telegram каналов.

Этот модуль содержит:
- Подключение к Telegram API через Telethon
- Парсинг сообщений из указанных каналов
- Сохранение новостей в ClickHouse
- Обработка медиафайлов и форматирование текста
- Автоматическую категоризацию новостей
"""

import asyncio
import re
import os
import sys
from datetime import datetime
from clickhouse_driver import Client as ClickHouseClient
from dotenv import load_dotenv

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials
# You need to get these from https://my.telegram.org/
API_ID = Config.TELEGRAM_API_ID
API_HASH = Config.TELEGRAM_API_HASH
PHONE = Config.TELEGRAM_PHONE  # Your phone number with country code

# List of Telegram channels to parse (use channel usernames without @)
TELEGRAM_CHANNELS = [
    'infantmilitario',
    'genshtab24',
    'new_militarycolumnist',
    'inosmichannel',
    'operline_ru'
    # Add more channels as needed
]

def create_table_if_not_exists():
    """Создание таблицы в ClickHouse для хранения Telegram новостей.
    
    Создает базу данных 'news' и таблицу 'telegram_headlines'
    с полями для хранения заголовков, контента, канала и метаданных.
    """
    client = ClickHouseClient(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Create database if not exists
    client.execute('CREATE DATABASE IF NOT EXISTS news')
    
    # Create table if not exists
    client.execute('''
    CREATE TABLE IF NOT EXISTS news.telegram_headlines (
        id UUID DEFAULT generateUUIDv4(),
        title String,
        content String,
        channel String,
        message_id Int64,
        message_link String,
        source String DEFAULT 'telegram',
        category String DEFAULT 'other',
        parsed_date DateTime DEFAULT now()
    ) ENGINE = MergeTree()
    ORDER BY (parsed_date, id)
    ''')

async def get_telegram_messages(client, channel, limit=100):
    """Получение сообщений из Telegram канала.
    
    Args:
        client: Telegram клиент
        channel (str): Имя канала без @
        limit (int): Максимальное количество сообщений
    
    Returns:
        tuple: (messages, entity) - Список сообщений и entity канала
    """
    try:
        entity = await client.get_entity(channel)
        
        # Get messages
        history = await client(GetHistoryRequest(
            peer=entity,
            offset_id=0,
            offset_date=None,
            add_offset=0,
            limit=limit,
            max_id=0,
            min_id=0,
            hash=0
        ))
        
        return history.messages, entity
    
    except Exception as e:
        print(f"Error getting messages from {channel}: {e}")
        return [], None

def clean_text(text):
    """Clean text from special characters and extra spaces"""
    if not text:
        return ""
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove special characters and extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def determine_category(channel):
    """Определение категории новостей на основе канала.
    
    Args:
        channel (str): Имя канала
    
    Returns:
        str: Категория новостей
    """
    military_channels = ['infantmilitario', 'genshtab24', 'new_militarycolumnist', 'operline_ru']
    international_channels = ['inosmichannel']
    
    if channel in military_channels:
        return 'military'
    elif channel in international_channels:
        return 'international'
    else:
        return 'other'

async def parse_telegram_channels():
    """Основная функция парсинга Telegram каналов.
    
    Подключается к Telegram API, получает сообщения из каналов,
    обрабатывает их и сохраняет в ClickHouse.
    """
    # Create table if not exists
    create_table_if_not_exists()
    
    # Initialize Telegram client with session file
    session_file = os.path.join(os.path.dirname(__file__), 'telegram_session')
    client = TelegramClient(session_file, API_ID, API_HASH)
    
    try:
        print("Connecting to Telegram...")
        await client.start(phone=PHONE)
        print("Successfully connected to Telegram")
        
        # Check if we're authorized
        if not await client.is_user_authorized():
            print("User not authorized. Please run this script interactively first to authorize.")
            return
        
        # Initialize ClickHouse client
        clickhouse_client = ClickHouseClient(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
        
        # Get existing message IDs to avoid duplicates
        existing_messages = {}
        for channel in TELEGRAM_CHANNELS:
            try:
                result = clickhouse_client.execute(
                    'SELECT message_id FROM news.telegram_headlines WHERE channel = %s',
                    [channel]
                )
                existing_messages[channel] = {row[0] for row in result}
            except Exception as e:
                print(f"Warning: Could not get existing messages for {channel}: {e}")
                existing_messages[channel] = set()
        
        # Parse each channel
        for channel in TELEGRAM_CHANNELS:
            try:
                print(f"\nParsing channel: {channel}")
                
                # Get messages from channel
                messages, entity = await get_telegram_messages(client, channel, limit=50)
                
                if not messages or not entity:
                    print(f"Could not get messages from {channel}")
                    continue
                
                # Determine category based on channel
                category = determine_category(channel)
                
                headlines_data = []
                skipped_count = 0
                
                for message in messages:
                    # Skip empty messages
                    if not message.message:
                        continue
                    
                    # Check if this message already exists in the database
                    if message.id in existing_messages.get(channel, set()):
                        skipped_count += 1
                        continue
                    
                    # Extract title (first line) and content
                    message_text = message.message
                    title_match = re.match(r'^(.+?)(?:\n|$)', message_text)
                    title = clean_text(title_match.group(1)) if title_match else "No title"
                    content = clean_text(message_text)
                    
                    # Create message link
                    message_link = f"https://t.me/{entity.username}/{message.id}" if hasattr(entity, 'username') else ""
                    
                    print(f"Title: {title[:50]}{'...' if len(title) > 50 else ''}")
                    print(f"Message ID: {message.id}")
                    print("-" * 40)
                    
                    # Add to data for insertion
                    headlines_data.append({
                        'title': title,
                        'content': content,
                        'channel': channel,
                        'message_id': message.id,
                        'message_link': message_link,
                        'category': category,
                        'source': 'telegram',
                        'parsed_date': datetime.now()
                    })
                
                # Insert data into ClickHouse if we have any
                if headlines_data:
                    clickhouse_client.execute(
                        'INSERT INTO news.telegram_headlines (title, content, channel, message_id, message_link, category, source, parsed_date) VALUES',
                        headlines_data
                    )
                    print(f"Added {len(headlines_data)} records to database from channel {channel}")
                
                if skipped_count > 0:
                    print(f"Skipped {skipped_count} duplicates from channel {channel}")
                
            except Exception as e:
                print(f"Error processing channel {channel}: {e}")
            
            # Sleep to avoid rate limiting
            await asyncio.sleep(2)
    
    finally:
        await client.disconnect()

if __name__ == "__main__":
    # Create .env file if it doesn't exist
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("TELEGRAM_API_ID=\nTELEGRAM_API_HASH=\nTELEGRAM_PHONE=\n")
        print("Created .env file. Please fill in your Telegram API credentials.")
        print("You can get API_ID and API_HASH from https://my.telegram.org/")
        exit(1)
    
    # Check if credentials are set
    if not API_ID or not API_HASH or not PHONE:
        print("Please set your Telegram API credentials in the .env file")
        exit(1)
    
    # Run the parser
    asyncio.run(parse_telegram_channels())