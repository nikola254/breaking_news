from telethon import TelegramClient, events
from telethon.tl.functions.messages import GetHistoryRequest
from clickhouse_driver import Client as ClickHouseClient
from datetime import datetime
import asyncio
import re
import os
import sys
from dotenv import load_dotenv

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Load environment variables from .env file
load_dotenv()

# Telegram API credentials
# You need to get these from https://my.telegram.org/
API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
PHONE = os.getenv('TELEGRAM_PHONE')  # Your phone number with country code

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
    """Create ClickHouse table if it doesn't exist"""
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
    """Get messages from a Telegram channel"""
    entity = await client.get_entity(channel)
    
    # Get messages
    messages = await client(GetHistoryRequest(
        peer=entity,
        limit=limit,
        offset_date=None,
        offset_id=0,
        max_id=0,
        min_id=0,
        add_offset=0,
        hash=0
    ))
    
    return messages.messages, entity

def clean_text(text):
    """Clean text from special characters and extra spaces"""
    if not text:
        return ""
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    # Remove special characters and extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    return text

async def parse_telegram_channels():
    """Parse messages from Telegram channels and save to ClickHouse"""
    # Create ClickHouse table if it doesn't exist
    create_table_if_not_exists()
    
    # Connect to ClickHouse
    clickhouse_client = ClickHouseClient(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Get existing message IDs to avoid duplicates
    existing_messages = {}
    for channel in TELEGRAM_CHANNELS:
        channel_messages = clickhouse_client.execute(
            f"SELECT message_id FROM news.telegram_headlines WHERE channel = '{channel}'"
        )
        existing_messages[channel] = set(row[0] for row in channel_messages)
    
    # Initialize Telegram client
    async with TelegramClient('telegram_parser_session', API_ID, API_HASH) as client:
        # Login if needed
        if not await client.is_user_authorized():
            await client.send_code_request(PHONE)
            code = input('Enter the code you received: ')
            await client.sign_in(PHONE, code)
        
        # Process each channel
        for channel in TELEGRAM_CHANNELS:
            try:
                print(f"Processing channel: {channel}")
                messages, entity = await get_telegram_messages(client, channel)
                
                # Prepare data for batch insert
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