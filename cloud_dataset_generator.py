#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор ChatML датасета с использованием Cloud.ru Foundation Models API
Для генерации логических вопросов к новостным фактам
"""

import json
import os
import re
import random
from datetime import datetime
from typing import List, Dict, Any, Optional
import requests
import urllib3
from config import Config

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class CloudDatasetGenerator:
    def __init__(self):
        self.config = Config()
        self.api_key = os.getenv('API_KEY')  # Cloud.ru API ключ
        self.api_url = "https://foundation-models.api.cloud.ru/v1"  # Базовый URL для Cloud.ru API
        
        # Критерии фильтрации качественных новостей
        self.min_text_length = 100
        self.max_text_length = 5000
        self.spam_keywords = [
            'подписывайтесь', 'лайк', 'репост', 'канал', 'телеграм',
            'реклама', 'скидка', 'акция', 'промокод', 'бесплатно',
            'заработок', 'инвестиции', 'криптовалюта', 'форекс'
        ]
        
        # Ключевые слова для новостей
        self.news_keywords = [
            'новости', 'сообщает', 'заявил', 'объявил', 'произошло',
            'случилось', 'событие', 'инцидент', 'ситуация', 'факт',
            'данные', 'информация', 'источник', 'эксперт', 'аналитик',
            'исследование', 'отчет', 'статистика', 'darpa', 'cia',
            'пентагон', 'министерство', 'правительство', 'президент'
        ]
        
    def generate_question_with_cloud_api(self, news_text: str) -> str:
        """
        Генерирует вопрос к новости используя Cloud.ru Foundation Models API
        """
        if not self.api_key:
            print("⚠️  API ключ не найден, используем резервный вопрос")
            return self._get_fallback_question()
            
        try:
            print(f"🔄 Отправляем запрос к Cloud.ru API...")
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                "model": "Qwen/Qwen3-Coder-480B-A35B-Instruct",
                "max_tokens": 100,
                "temperature": 0.7,
                "presence_penalty": 0,
                "top_p": 0.95,
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты помощник для создания вопросов к новостным текстам. Создавай краткие, логичные вопросы на русском языке."
                    },
                    {
                        "role": "user",
                        "content": f"Создай один логический вопрос на русском языке к следующей новости. Вопрос должен быть конкретным и помогать понять суть события. Вопрос должен начинаться с вопросительного слова (Что, Как, Где, Когда, Почему, Кто).\n\nНовость: {news_text[:1000]}\n\nВопрос:"
                    }
                ]
            }
            
            print(f"📡 Выполняем POST запрос к {self.api_url}/chat/completions")
            print(f"📝 Длина текста новости: {len(news_text)} символов")
            
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30,
                verify=False
            )
            
            print(f"📊 Получен ответ со статусом: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                question = result['choices'][0]['message']['content'].strip()
                print(f"✅ Вопрос сгенерирован: {question[:50]}...")
            else:
                print(f"❌ API вернул код {response.status_code}: {response.text}")
                print(f"🔄 Используем резервный вопрос")
                return self._get_fallback_question()
            
            # Очистка вопроса от лишних символов
            question = re.sub(r'^["\']|["\']$', '', question)
            question = question.strip()
            
            if question and len(question) > 10:
                print(f"✅ Финальный вопрос: {question}")
                return question
            else:
                print(f"⚠️  Сгенерированный вопрос слишком короткий, используем резервный")
                
        except Exception as e:
            print(f"❌ Ошибка при обращении к Cloud.ru API: {e}")
            print(f"🔄 Используем резервный вопрос")
            
        return self._get_fallback_question()
    
    def _get_fallback_question(self) -> str:
        """
        Возвращает случайный вопрос из предустановленных шаблонов
        """
        import random
        
        fallback_questions = [
            "Что произошло согласно данной новости?",
            "Какие ключевые факты содержатся в этом сообщении?",
            "Что стало известно из данной информации?",
            "Какие события описываются в новости?",
            "Что случилось по данным этого сообщения?",
            "Какие детали приводятся в данном материале?",
            "О чем сообщается в данной новости?",
            "Какая информация содержится в этом сообщении?"
        ]
        
        return random.choice(fallback_questions)
    
    def is_valid_news_item(self, item: Dict) -> bool:
        """
        Проверяет, является ли элемент валидной новостной записью
        """
        if not isinstance(item, dict):
            return False
        
        text = item.get('text', '')
        if not text or len(text.strip()) < 50:
            return False
        
        # Фильтруем служебные сообщения
        service_keywords = ['подписывайтесь', 'канал', 'реклама', 'спонсор']
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in service_keywords):
            return False
        
        return True
    
    def is_valid_telegram_message(self, message: Dict) -> bool:
        """
        Проверяет, является ли Telegram сообщение валидным для обработки
        """
        if not isinstance(message, dict):
            return False
        
        # Проверяем тип сообщения
        if message.get('type') != 'message':
            return False
        
        # Извлекаем текст из сложной структуры
        text = self.extract_telegram_text(message)
        if not text or len(text.strip()) < 100:
            return False
        
        # Фильтруем служебные сообщения
        service_keywords = ['подписывайтесь', '@', 'канал', 'реклама', 'спонсор', 'репост']
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in service_keywords):
            return False
        
        return True
    
    def extract_telegram_text(self, message: Dict) -> str:
        """
        Извлекает текст из сложной структуры Telegram сообщения
        """
        text_parts = message.get('text', [])
        if isinstance(text_parts, str):
            return text_parts
        
        if isinstance(text_parts, list):
            full_text = ""
            for part in text_parts:
                if isinstance(part, str):
                    full_text += part
                elif isinstance(part, dict) and 'text' in part:
                    full_text += part['text']
            return full_text
        
        return ""
    
    def create_chatml_entry_from_telegram(self, message: Dict) -> Dict:
        """
        Создает ChatML запись из Telegram сообщения
        """
        text = self.extract_telegram_text(message)
        if not text:
            return None
        
        # Создаем структуру как для обычной новости
        news_item = {
            'text': text,
            'date': message.get('date', ''),
            'source': 'telegram',
            'id': message.get('id', '')
        }
        
        return self.create_chatml_entry(news_item)
    
    def is_quality_message(self, message_data: Dict[str, Any]) -> bool:
        """
        Проверяет, является ли сообщение качественной новостью
        """
        text = self.extract_text_from_message(message_data)
        
        if not text or len(text) < self.min_text_length:
            return False
            
        if len(text) > self.max_text_length:
            return False
            
        text_lower = text.lower()
        
        # Проверка на спам
        spam_count = sum(1 for keyword in self.spam_keywords if keyword in text_lower)
        if spam_count >= 2:
            return False
            
        # Проверка на наличие новостных ключевых слов
        news_count = sum(1 for keyword in self.news_keywords if keyword in text_lower)
        if news_count == 0:
            return False
            
        # Проверка на количество ссылок
        link_count = len(re.findall(r'http[s]?://\S+', text))
        if link_count > 3:
            return False
            
        # Проверка на наличие знаков препинания (признак структурированного текста)
        punctuation_count = len(re.findall(r'[.!?;:]', text))
        if punctuation_count < 2:
            return False
            
        return True
    
    def extract_text_from_message(self, message_data: Dict[str, Any]) -> str:
        """
        Извлекает текст из сообщения Telegram
        """
        text_parts = []
        
        # Основной текст сообщения
        if 'text' in message_data:
            if isinstance(message_data['text'], str):
                text_parts.append(message_data['text'])
            elif isinstance(message_data['text'], list):
                for item in message_data['text']:
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
        
        # Подпись к медиа
        if 'caption' in message_data:
            if isinstance(message_data['caption'], str):
                text_parts.append(message_data['caption'])
            elif isinstance(message_data['caption'], list):
                for item in message_data['caption']:
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
        
        return ' '.join(text_parts).strip()
    
    def create_chatml_entry(self, message_data: Dict[str, Any], use_ai: bool = True) -> Dict[str, Any]:
        """
        Создает запись в формате ChatML
        """
        text = self.extract_text_from_message(message_data)
        
        if use_ai:
            question = self.generate_question_with_cloud_api(text)
        else:
            question = self._get_fallback_question()
        
        return {
            "messages": [
                {
                    "role": "user",
                    "content": question
                },
                {
                    "role": "assistant",
                    "content": text
                }
            ]
        }
    
    def process_json_file(self, file_path: str, use_ai: bool = True) -> List[Dict[str, Any]]:
        """
        Обрабатывает один JSON файл и возвращает список ChatML записей
        """
        chatml_entries = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            messages = []
            # Обрабатываем экспорт Telegram канала
            if isinstance(data, dict) and 'messages' in data:
                print(f"📱 Обрабатываем Telegram канал: {data.get('name', 'Неизвестный')}")
                messages = data['messages']
                print(f"🔢 Обрабатываем {len(messages)} сообщений")
            elif isinstance(data, list):
                messages = data
            
            for message in messages:
                if isinstance(message, dict) and self.is_quality_message(message):
                    entry = self.create_chatml_entry(message, use_ai)
                    chatml_entries.append(entry)
                    
        except Exception as e:
            print(f"Ошибка при обработке файла {file_path}: {e}")
        
        return chatml_entries
    
    def generate_dataset(self, input_dir: str = "dataset/input", output_dir: str = "dataset/output", use_ai: bool = True):
        """
        Генерирует полный датасет из всех JSON файлов
        """
        if not os.path.exists(input_dir):
            print(f"Папка {input_dir} не найдена")
            return
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        all_entries = []
        json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
        
        print(f"Найдено {len(json_files)} JSON файлов")
        
        try:
            for i, filename in enumerate(json_files, 1):
                file_path = os.path.join(input_dir, filename)
                print(f"Обрабатываем файл {i}/{len(json_files)}: {filename}")
                
                entries = self.process_json_file(file_path, use_ai)
                all_entries.extend(entries)
                
                print(f"  Создано {len(entries)} записей")
                
                # Сохраняем промежуточные результаты каждые 10 файлов
                if i % 10 == 0 or i == len(json_files):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ai_suffix = "_cloud_ai" if use_ai else "_templates"
                    temp_filename = f"chatml_dataset{ai_suffix}_temp_{i}files_{timestamp}.json"
                    temp_path = os.path.join(output_dir, temp_filename)
                    
                    with open(temp_path, 'w', encoding='utf-8') as f:
                        json.dump(all_entries, f, ensure_ascii=False, indent=2)
                    
                    print(f"  💾 Промежуточное сохранение: {temp_filename} ({len(all_entries)} записей)")
        
        except KeyboardInterrupt:
            print(f"\n⚠️  Обработка прервана пользователем")
            print(f"📊 Обработано файлов: {i}/{len(json_files)}")
            print(f"📝 Создано записей: {len(all_entries)}")
            
            if all_entries:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                ai_suffix = "_cloud_ai" if use_ai else "_templates"
                partial_filename = f"chatml_dataset{ai_suffix}_partial_{i}files_{timestamp}.json"
                partial_path = os.path.join(output_dir, partial_filename)
                
                with open(partial_path, 'w', encoding='utf-8') as f:
                    json.dump(all_entries, f, ensure_ascii=False, indent=2)
                
                print(f"💾 Частичный датасет сохранен: {partial_filename}")
                return partial_path
            
            return None
        
        # Сохранение результата
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ai_suffix = "_cloud_ai" if use_ai else "_templates"
        output_filename = f"chatml_dataset{ai_suffix}_{timestamp}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_entries, f, ensure_ascii=False, indent=2)
        
        print(f"\nДатасет сохранен: {output_path}")
        print(f"Всего создано {len(all_entries)} ChatML записей")
        
        return output_path

def main():
    generator = CloudDatasetGenerator()
    
    print("Генератор ChatML датасета с Cloud.ru Foundation Models API")
    print("=" * 60)
    
    # Проверка наличия API ключа
    if not generator.api_key:
        print("⚠️  API ключ Cloud.ru не найден в переменных окружения")
        print("Будут использоваться предустановленные шаблоны вопросов")
        use_ai = False
    else:
        print("✅ API ключ Cloud.ru найден")
        use_ai = True
    
    # Генерация датасета
    output_path = generator.generate_dataset(use_ai=use_ai)
    
    if output_path:
        print(f"\n✅ Датасет успешно создан: {output_path}")
    else:
        print("\n❌ Ошибка при создании датасета")

if __name__ == "__main__":
    main()