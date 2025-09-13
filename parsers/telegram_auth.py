#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для первоначальной авторизации в Telegram API.
Запустите этот скрипт интерактивно для создания сессии.
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config
from telethon import TelegramClient

# Load environment variables
load_dotenv()

# Telegram API credentials
API_ID = Config.TELEGRAM_API_ID
API_HASH = Config.TELEGRAM_API_HASH
PHONE = Config.TELEGRAM_PHONE

async def authorize_telegram():
    """Авторизация в Telegram API и создание сессии."""
    
    if not API_ID or not API_HASH or not PHONE:
        print("Ошибка: Не заданы параметры Telegram API в .env файле")
        print("Необходимо указать: TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE")
        return False
    
    # Create session file path
    session_file = os.path.join(os.path.dirname(__file__), 'telegram_session')
    
    print(f"Создание сессии Telegram...")
    print(f"Телефон: {PHONE}")
    print(f"Файл сессии: {session_file}")
    
    client = TelegramClient(session_file, API_ID, API_HASH)
    
    try:
        await client.start(phone=PHONE)
        
        if await client.is_user_authorized():
            print("✅ Успешная авторизация в Telegram!")
            print(f"Сессия сохранена в: {session_file}.session")
            
            # Test getting user info
            me = await client.get_me()
            print(f"Авторизован как: {me.first_name} {me.last_name or ''} (@{me.username or 'no_username'})")
            
            return True
        else:
            print("❌ Не удалось авторизоваться")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        return False
    finally:
        await client.disconnect()

if __name__ == "__main__":
    print("=== Авторизация в Telegram API ===")
    print("Этот скрипт создаст сессию для автоматического парсинга Telegram каналов.")
    print("Вам может потребоваться ввести код подтверждения из SMS или Telegram.")
    print()
    
    success = asyncio.run(authorize_telegram())
    
    if success:
        print("\n✅ Авторизация завершена успешно!")
        print("Теперь вы можете запускать parser_telegram.py без интерактивного ввода.")
    else:
        print("\n❌ Авторизация не удалась.")
        print("Проверьте настройки в .env файле и попробуйте снова.")