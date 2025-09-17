import asyncio
import logging
from typing import List, Dict, Optional, AsyncGenerator
from datetime import datetime, timedelta
import re
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User, MessageMediaPhoto, MessageMediaDocument
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import time
from ..ai.content_classifier import ExtremistContentClassifier

class TelegramAnalyzer:
    """Класс для работы с Telegram API и анализа контента"""
    
    def __init__(self, api_id: int, api_hash: str, phone_number: str, session_name: str = 'analyzer_session'):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.session_name = session_name
        self.client = None
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self, password: Optional[str] = None):
        """Инициализация клиента Telegram"""
        self.client = TelegramClient(self.session_name, self.api_id, self.api_hash)
        
        try:
            await self.client.start(phone=self.phone_number, password=password)
            self.logger.info("Telegram client initialized successfully")
        except SessionPasswordNeededError:
            if password:
                await self.client.start(phone=self.phone_number, password=password)
            else:
                raise Exception("Two-factor authentication enabled. Password required.")
        except Exception as e:
            self.logger.error(f"Failed to initialize Telegram client: {e}")
            raise
    
    async def search_channels(self, query: str, limit: int = 50) -> List[Dict]:
        """Поиск каналов по ключевым словам"""
        if not self.client:
            raise Exception("Client not initialized")
            
        channels = []
        
        try:
            # Поиск через глобальный поиск
            async for dialog in self.client.iter_dialogs(limit=1000):
                if hasattr(dialog.entity, 'title') and query.lower() in dialog.entity.title.lower():
                    if isinstance(dialog.entity, Channel):
                        channel_data = {
                            'id': dialog.entity.id,
                            'title': dialog.entity.title,
                            'username': dialog.entity.username,
                            'description': getattr(dialog.entity, 'about', ''),
                            'participants_count': getattr(dialog.entity, 'participants_count', 0),
                            'is_broadcast': dialog.entity.broadcast,
                            'is_megagroup': dialog.entity.megagroup,
                            'verified': getattr(dialog.entity, 'verified', False),
                            'restricted': getattr(dialog.entity, 'restricted', False),
                            'source': 'telegram_channel'
                        }
                        channels.append(channel_data)
                        
                        if len(channels) >= limit:
                            break
                            
        except Exception as e:
            self.logger.error(f"Error searching channels: {e}")
            
        return channels
    
    async def get_channel_info(self, channel_username: str) -> Optional[Dict]:
        """Получение информации о канале"""
        if not self.client:
            raise Exception("Client not initialized")
            
        try:
            entity = await self.client.get_entity(channel_username)
            
            if isinstance(entity, Channel):
                full_info = await self.client.get_entity(entity)
                
                return {
                    'id': entity.id,
                    'title': entity.title,
                    'username': entity.username,
                    'description': getattr(full_info, 'about', ''),
                    'participants_count': getattr(entity, 'participants_count', 0),
                    'is_broadcast': entity.broadcast,
                    'is_megagroup': entity.megagroup,
                    'verified': getattr(entity, 'verified', False),
                    'restricted': getattr(entity, 'restricted', False),
                    'date_created': entity.date,
                    'source': 'telegram_channel'
                }
                
        except Exception as e:
            self.logger.error(f"Error getting channel info for {channel_username}: {e}")
            return None
    
    async def get_channel_messages(self, channel_username: str, limit: int = 100, 
                                 offset_date: Optional[datetime] = None) -> List[Dict]:
        """Получение сообщений из канала"""
        if not self.client:
            raise Exception("Client not initialized")
            
        messages = []
        
        try:
            entity = await self.client.get_entity(channel_username)
            
            async for message in self.client.iter_messages(entity, limit=limit, offset_date=offset_date):
                if message.text:
                    # Обработка медиа
                    media_type = None
                    if message.media:
                        if isinstance(message.media, MessageMediaPhoto):
                            media_type = 'photo'
                        elif isinstance(message.media, MessageMediaDocument):
                            media_type = 'document'
                        else:
                            media_type = 'other'
                    
                    message_data = {
                        'id': message.id,
                        'text': message.text,
                        'date': message.date,
                        'views': getattr(message, 'views', 0),
                        'forwards': getattr(message, 'forwards', 0),
                        'replies': getattr(message.replies, 'replies', 0) if message.replies else 0,
                        'from_id': message.from_id.user_id if message.from_id else None,
                        'channel_id': entity.id,
                        'channel_title': entity.title,
                        'media_type': media_type,
                        'has_media': message.media is not None,
                        'message_url': f"https://t.me/{entity.username}/{message.id}" if entity.username else None,
                        'source': 'telegram_message'
                    }
                    messages.append(message_data)
                    
        except FloodWaitError as e:
            self.logger.warning(f"Rate limit hit, waiting {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            self.logger.error(f"Error getting messages from {channel_username}: {e}")
            
        return messages
    
    async def get_chat_messages(self, chat_id: int, limit: int = 100) -> List[Dict]:
        """Получение сообщений из чата"""
        if not self.client:
            raise Exception("Client not initialized")
            
        messages = []
        
        try:
            async for message in self.client.iter_messages(chat_id, limit=limit):
                if message.text:
                    message_data = {
                        'id': message.id,
                        'text': message.text,
                        'date': message.date,
                        'from_id': message.from_id.user_id if message.from_id else None,
                        'chat_id': chat_id,
                        'reply_to': message.reply_to_msg_id,
                        'has_media': message.media is not None,
                        'source': 'telegram_chat_message'
                    }
                    messages.append(message_data)
                    
        except Exception as e:
            self.logger.error(f"Error getting chat messages: {e}")
            
        return messages
    
    def analyze_content_batch(self, messages: List[Dict], keywords: List[str]) -> List[Dict]:
        """Анализ сообщений на наличие экстремистского контента с использованием ИИ классификатора"""
        analyzed_messages = []
        classifier = ExtremistContentClassifier()
        
        for message in messages:
            text = message.get('text', '')
            
            if not text.strip():
                # Если текста нет, помечаем как обычный контент
                analyzed_message = message.copy()
                analyzed_message.update({
                    'classification': 'normal',
                    'confidence': 0.1,
                    'risk_score': 0,
                    'risk_level': 'none',
                    'extremism_percentage': 0,
                    'found_keywords': [],
                    'highlighted_text': text,
                    'threat_color': '#28a745',
                    'detected_keywords': [],
                    'analysis_date': datetime.now(),
                    'analysis_method': 'empty_content'
                })
                analyzed_messages.append(analyzed_message)
                continue
            
            # Используем новый метод определения процента экстремизма через облачную модель
            extremism_analysis = classifier.analyze_extremism_percentage(text)
            
            # Дополнительные факторы риска для Telegram
            social_risk_bonus = 0
            if message.get('views', 0) > 1000:
                social_risk_bonus += 5
            if message.get('forwards', 0) > 100:
                social_risk_bonus += 4
            if message.get('replies', 0) > 50:
                social_risk_bonus += 3
            if message.get('has_media', False):
                social_risk_bonus += 2
            if len(text) > 1000:
                social_risk_bonus += 2
            if '@' in text or 't.me/' in text:
                social_risk_bonus += 3  # Ссылки на каналы/пользователей
            
            # Корректируем процент экстремизма с учетом социальных факторов
            adjusted_extremism_percentage = min(100, extremism_analysis['extremism_percentage'] + social_risk_bonus)
            
            # Определяем уровень риска на основе процента экстремизма
            if adjusted_extremism_percentage >= 80:
                risk_level = 'critical'
            elif adjusted_extremism_percentage >= 60:
                risk_level = 'high'
            elif adjusted_extremism_percentage >= 40:
                risk_level = 'medium'
            elif adjusted_extremism_percentage >= 20:
                risk_level = 'low'
            else:
                risk_level = 'none'
            
            analyzed_message = message.copy()
            analyzed_message.update({
                'classification': 'extremist' if adjusted_extremism_percentage >= 40 else ('suspicious' if adjusted_extremism_percentage >= 20 else 'normal'),
                'confidence': extremism_analysis['confidence'],
                'risk_score': adjusted_extremism_percentage,
                'risk_level': risk_level,
                'extremism_percentage': adjusted_extremism_percentage,
                'found_keywords': extremism_analysis.get('detected_keywords', []),
                'highlighted_text': text,  # Можно добавить выделение ключевых слов
                'threat_color': '#dc3545' if risk_level == 'critical' else ('#fd7e14' if risk_level == 'high' else ('#ffc107' if risk_level == 'medium' else ('#28a745' if risk_level == 'none' else '#6c757d'))),
                'detected_keywords': extremism_analysis.get('detected_keywords', []),
                'analysis_date': datetime.now(),
                'analysis_method': extremism_analysis.get('method', 'unknown'),
                'explanation': extremism_analysis.get('explanation', ''),
                'social_risk_bonus': social_risk_bonus
            })
            
            analyzed_messages.append(analyzed_message)
        
        return analyzed_messages
    
    async def monitor_channels(self, channel_usernames: List[str], keywords: List[str], 
                             hours_back: int = 24) -> List[Dict]:
        """Мониторинг каналов на предмет экстремистского контента"""
        all_messages = []
        start_date = datetime.now() - timedelta(hours=hours_back)
        
        for username in channel_usernames:
            try:
                messages = await self.get_channel_messages(username, limit=200, offset_date=start_date)
                analyzed_messages = self.analyze_content_batch(messages, keywords)
                
                # Фильтруем только подозрительный контент
                suspicious_messages = [
                    msg for msg in analyzed_messages 
                    if msg['risk_level'] in ['medium', 'high', 'critical']
                ]
                
                all_messages.extend(suspicious_messages)
                
                # Пауза между запросами
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"Error monitoring channel {username}: {e}")
                continue
        
        # Сортируем по уровню риска и дате
        all_messages.sort(key=lambda x: (x['risk_score'], x['date']), reverse=True)
        
        return all_messages
    
    async def real_time_monitor(self, channel_usernames: List[str], keywords: List[str]):
        """Мониторинг в реальном времени"""
        if not self.client:
            raise Exception("Client not initialized")
            
        @self.client.on(events.NewMessage)
        async def handler(event):
            if hasattr(event.chat, 'username') and event.chat.username in channel_usernames:
                if event.text:
                    message_data = {
                        'id': event.id,
                        'text': event.text,
                        'date': event.date,
                        'from_id': event.from_id.user_id if event.from_id else None,
                        'channel_id': event.chat_id,
                        'channel_title': event.chat.title,
                        'source': 'telegram_realtime'
                    }
                    
                    analyzed = self.analyze_content_batch([message_data], keywords)
                    
                    if analyzed and analyzed[0]['risk_level'] in ['medium', 'high', 'critical']:
                        self.logger.warning(f"Suspicious content detected: {analyzed[0]}")
                        # Здесь можно добавить отправку уведомлений
        
        self.logger.info("Real-time monitoring started")
        await self.client.run_until_disconnected()
    
    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        if not self.client:
            raise Exception("Client not initialized")
            
        try:
            user = await self.client.get_entity(user_id)
            
            if isinstance(user, User):
                return {
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                    'phone': user.phone,
                    'verified': getattr(user, 'verified', False),
                    'restricted': getattr(user, 'restricted', False),
                    'bot': user.bot,
                    'source': 'telegram_user'
                }
                
        except Exception as e:
            self.logger.error(f"Error getting user info for {user_id}: {e}")
            return None
    
    async def close(self):
        """Закрытие соединения"""
        if self.client:
            await self.client.disconnect()

# Пример использования
async def main():
    # Инициализация анализатора
    telegram_analyzer = TelegramAnalyzer(
        api_id=12345,  # Ваш API ID
        api_hash="your_api_hash",  # Ваш API Hash
        phone_number="+1234567890"  # Ваш номер телефона
    )
    
    try:
        # Инициализация клиента
        await telegram_analyzer.initialize()
        
        # Поиск каналов
        channels = await telegram_analyzer.search_channels('новости', limit=10)
        
        # Мониторинг каналов
        keywords = ['экстремизм', 'терроризм', 'радикализм']
        channel_usernames = [ch['username'] for ch in channels if ch['username']]
        
        suspicious_content = await telegram_analyzer.monitor_channels(channel_usernames, keywords)
        
        # Вывод результатов
        for content in suspicious_content:
            print(f"Риск: {content['risk_level']}, Канал: {content['channel_title']}, Текст: {content['text'][:100]}...")
            
    finally:
        await telegram_analyzer.close()

if __name__ == "__main__":
    asyncio.run(main())