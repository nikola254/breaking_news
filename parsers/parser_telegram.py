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

# Добавляем путь к парсерам для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__)))
from gen_api_classifier import GenApiNewsClassifier
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
    'operline_ru',
    'rian_ru',           # РИА Новости
    'bbcrussian',        # BBC Russian
    'meduzalive',        # Медуза
    'breakingmash',      # Mash
    'readovkanews'       # Readovka
    # Add more channels as needed
]

def create_ukraine_tables_if_not_exists():
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
        published_date DateTime DEFAULT now()
    ) ENGINE = MergeTree()
    ORDER BY (published_date, id)
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
    """Очистка текста от рекламы, призывов к подписке и лишних символов"""
    if not text:
        return ""
    
    # Обработка кодировки
    try:
        text = str(text)
    except UnicodeDecodeError:
        text = text.encode('utf-8', errors='replace').decode('utf-8')
    
    # Проверка на сообщения состоящие только из эмодзи
    emoji_pattern = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U0001F018-\U0001F0F5\U0001F200-\U0001F2FF]+'
    emoji_only = re.sub(r'[^\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF\U0001F018-\U0001F0F5\U0001F200-\U0001F2FF\s]', '', text).strip()
    
    # Если сообщение состоит только из эмодзи и пробелов - это спам
    if emoji_only and len(emoji_only) > 0 and len(text.strip()) < 50:
        return ""
    
    # Проверка на слишком много эмодзи (>30% от текста)
    emoji_count = len(re.findall(emoji_pattern, text))
    text_length = len(re.sub(emoji_pattern, '', text).strip())
    if emoji_count > 0 and text_length > 0 and (emoji_count / (emoji_count + text_length)) > 0.3:
        return ""
    
    # Проверка на слишком короткие сообщения без смысла
    if len(text.strip()) < 20:
        return ""
    
    # Удаляем URL-адреса
    text = re.sub(r'https?://\S+', '', text)
    
    # Удаляем призывы к подписке (различные варианты)
    spam_patterns = [
        r'[❗️⚡🔥💥]*\s*[Пп]одпис[ыь]вайся?\s+на\s+\S+',  # Подписывайся на Mash
        r'[Пп]одпиш[иеу]тес?ь?\s+на\s+\S+',  # Подпишитесь на канал
        r'[Пп]одпиш[иеу]тес?ь?\s+➡️?\s*\S+',  # Подпишитесь ➡️
        r'[Чч]итай(?:те)?\s+(?:нас|наш\s+канал)',  # Читайте нас
        r'[Сс]ледите?\s+за\s+(?:нами|обновлениями)',  # Следите за нами
        r'[Вв]ступай(?:те)?\s+в\s+(?:наш)?\s*(?:канал|группу)',  # Вступайте в канал
        r'[Жж]ми\s+➡️?\s*\S+',  # Жми ➡️
        r'➡️\s*[Пп]одпис',  # ➡️ Подпис
        r'@\w+\s*[-–—]\s*подпис',  # @channel - подпис
        r'[Ии]сточник:\s*@?\w+',  # Источник: @channel
        r'\|\s*[Пп]одпис',  # | Подпис
        r'🔔\s*[Пп]одпис',  # 🔔 Подпис
        r'[Пп]одпис[ыь]вайся?\s*[❗️⚡🔥💥]*',  # Подписывайся!
        r'[Пп]одпиш[иеу]тес?ь?\s*[❗️⚡🔥💥]*',  # Подпишитесь!
        r'[Сс]ледите?\s+за\s+нами\s*[❗️⚡🔥💥]*',  # Следите за нами!
    ]
    
    for pattern in spam_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Удаляем эмодзи в начале и конце строк (типа ❗, ⚡, 🔥 и т.д.)
    text = re.sub(r'^[❗️⚡🔥💥🚨⭐️✅❌⛔️🔴🟢🔵⚪️🟡🟣🟤⬛️⬜️▪️▫️]+\s*', '', text)
    text = re.sub(r'\s*[❗️⚡🔥💥🚨⭐️✅❌⛔️🔴🟢🔵⚪️🟡🟣🟤⬛️⬜️▪️▫️]+$', '', text)
    
    # Удаляем повторяющиеся эмодзи внутри текста (более 2 подряд)
    text = re.sub(r'([❗️⚡🔥💥🚨⭐️✅❌⛔️])\1{2,}', r'\1', text)
    
    # Удаляем строки, которые состоят только из символов и эмодзи
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        # Удаляем пустые строки и строки только из символов
        stripped = re.sub(r'[❗️⚡🔥💥🚨⭐️✅❌⛔️🔴🟢🔵⚪️🟡🟣🟤⬛️⬜️▪️▫️➡️🔔|—–-]+', '', line).strip()
        if stripped and len(stripped) > 10:  # Минимальная длина строки
            clean_lines.append(line)
    
    text = '\n'.join(clean_lines)
    
    # Удаляем множественные пробелы и символы
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Удаляем оставшиеся одиночные эмодзи призывов
    text = re.sub(r'^\s*[❗️⚡🔥➡️🔔]\s*', '', text)
    text = re.sub(r'\s*[❗️⚡🔥➡️🔔]\s*$', '', text)
    
    # Финальная проверка - если после очистки осталось меньше 20 символов, это спам
    if len(text.strip()) < 20:
        return ""
    
    return text

def determine_category(title, content, channel):
    """Определение категории новостей с использованием классификатора.
    
    Args:
        title (str): Заголовок новости
        content (str): Содержание новости
        channel (str): Имя канала
    
    Returns:
        str: Категория новостей или None для категории 'other'
    """
    try:
        # Импортируем классификатор
        from parsers.improved_classifier import classifier
        
        # Классифицируем текст (передаем title и content отдельно)
        category = classifier.classify(title, content)
        
        # Пропускаем статьи категории "other"
        if category == 'other':
            return None
            
        return category
        
    except Exception as e:
        print(f"Error classifying message: {e}")
        # В случае ошибки используем базовую логику по каналам
        military_channels = ['infantmilitario', 'genshtab24', 'new_militarycolumnist', 'operline_ru']
        
        if channel in military_channels:
            return 'military_operations'
        else:
            return 'information_social'

async def parse_telegram_channels(limit=None):
    """Основная функция парсинга Telegram каналов.
    
    Подключается к Telegram API, получает сообщения из каналов,
    обрабатывает их и сохраняет в ClickHouse.
    """
    # Create table if not exists
    create_ukraine_tables_if_not_exists()
    
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
                    f"SELECT message_id FROM news.telegram_headlines WHERE channel = '{channel}'"
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
                messages_limit = limit if limit else 100
                messages, entity = await get_telegram_messages(client, channel, limit=messages_limit)
                
                if not messages or not entity:
                    print(f"Could not get messages from {channel}")
                    continue
                
                headlines_data = []
                skipped_count = 0
                skipped_other_count = 0
                
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
                    
                    # Пропускаем сообщения без контента после очистки
                    if not content or len(content.strip()) < 20:
                        print(f"Skipped spam/empty message: {message_text[:50]}...")
                        continue
                    
                    # Дополнительная классификация через Gen-API для получения индексов напряженности
                    try:
                        classifier = GenApiNewsClassifier()
                        ai_result = classifier.classify(title, content)
                        
                        # Используем результаты Gen-API классификации
                        category = ai_result['category_name']
                        social_tension_index = ai_result['social_tension_index']
                        spike_index = ai_result['spike_index']
                        ai_confidence = ai_result['confidence']
                        ai_category = ai_result['category_name']
                        
                        print(f"Gen-API классификация: {category} (напряженность: {social_tension_index}, всплеск: {spike_index})")
                        
                    except Exception as e:
                        print(f"Ошибка Gen-API классификации: {e}")
                        # Fallback к результатам improved_classifier
                        category_result = determine_category(title, content, channel)
                        if isinstance(category_result, tuple):
                            category = category_result[0]  # Берем только название категории
                        else:
                            category = category_result
                        social_tension_index = 0.0
                        spike_index = 0.0
                        ai_confidence = 0.0
                        ai_category = category

                    # Skip if category is None (other category)
                    if category is None:
                        skipped_other_count += 1
                        continue
                    
                    # Create message link
                    message_link = f"https://t.me/{entity.username}/{message.id}" if hasattr(entity, 'username') else ""
                    
                    # Безопасный вывод с обработкой кодировки
                    try:
                        safe_title = title[:50] + ('...' if len(title) > 50 else '')
                        print(f"Title: {safe_title}")
                        print(f"Category: {category}")
                    except UnicodeEncodeError:
                        # Если есть проблемы с кодировкой, заменяем проблемные символы
                        safe_title = title.encode('utf-8', errors='replace').decode('utf-8')[:50]
                        print(f"Title: {safe_title}{'...' if len(title) > 50 else ''}")
                        print(f"Category: {category}")
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
                        'social_tension_index': social_tension_index,
                        'spike_index': spike_index,
                        'ai_category': ai_category,
                        'ai_confidence': ai_confidence,
                        'ai_classification_metadata': 'gen_api_classification',
                        'published_date': datetime.now()
                    })
                
                # Insert data into ClickHouse if we have any
                if headlines_data:
                    clickhouse_client.execute(
                        'INSERT INTO news.telegram_headlines (title, content, channel, message_id, message_link, category, source, social_tension_index, spike_index, ai_category, ai_confidence, ai_classification_metadata, published_date) VALUES',
                        headlines_data
                    )
                    print(f"Added {len(headlines_data)} records to database from channel {channel}")
                
                if skipped_count > 0:
                    print(f"Skipped {skipped_count} duplicates from channel {channel}")
                
                if skipped_other_count > 0:
                    print(f"Skipped {skipped_other_count} 'other' category messages from channel {channel}")
                
            except Exception as e:
                print(f"Error processing channel {channel}: {e}")
            
            # Sleep to avoid rate limiting
            await asyncio.sleep(2)
    
    finally:
        await client.disconnect()

def main(limit=None):
    """Главная функция для запуска парсера"""
    try:
        print("Запуск парсера Telegram")
        
        # Парсинг каналов
        asyncio.run(parse_telegram_channels(limit=limit))
        
        print("Парсер Telegram завершил работу")
        sys.exit(0)
    except Exception as e:
        print(f"Критическая ошибка в парсере Telegram: {e}")
        sys.exit(1)

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
    import argparse
    parser = argparse.ArgumentParser(description='Parser for Telegram channels')
    parser.add_argument('--limit', type=int, default=None, help='Limit messages to parse (for testing)')
    args = parser.parse_args()
    
    main(limit=args.limit)
