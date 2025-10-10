#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модуль валидации и очистки контента новостей

Этот модуль содержит функции для:
- Валидации контента новостей
- Очистки от эмодзи, спама и призывов подписаться
- Фильтрации некачественного контента
- Проверки минимальных требований к тексту
"""

import re
import logging
from typing import Tuple, List, Optional

logger = logging.getLogger(__name__)

class ContentValidator:
    """Класс для валидации и очистки контента новостей"""
    
    def __init__(self):
        # Фразы, которые указывают на некачественный контент
        self.bad_content_phrases = [
            "не удалось извлечь содержимое",
            "не удалось извлечь",
            "содержимое недоступно",
            "ошибка загрузки",
            "страница не найдена",
            "контент временно недоступен",
            "подпишитесь на наш канал",
            "подпишитесь на нас",
            "следите за нами",
            "подписывайтесь",
            "ставьте лайки",
            "делитесь с друзьями",
            "репостите",
            "пересылайте",
            "читайте также",
            "смотрите также",
            "рекомендуем прочитать",
            "по теме",
            "похожие новости",
            "другие новости",
            "еще новости",
            "больше новостей",
            "все новости",
            "архив новостей",
            "новости за",
            "загружается",
            "загрузка",
            "loading",
            "please wait",
            "waiting",
            "ошибка",
            "error",
            "exception",
            "undefined",
            "null",
            "none"
        ]
        
        # Регулярные выражения для эмодзи
        self.emoji_patterns = [
            # Основные эмодзи Unicode
            r'[\U0001F600-\U0001F64F]',  # Emoticons
            r'[\U0001F300-\U0001F5FF]',  # Misc Symbols and Pictographs
            r'[\U0001F680-\U0001F6FF]',  # Transport and Map
            r'[\U0001F1E0-\U0001F1FF]',  # Regional indicator symbols
            r'[\U00002600-\U000026FF]',  # Miscellaneous symbols
            r'[\U00002700-\U000027BF]',  # Dingbats
            r'[\U0001F900-\U0001F9FF]',  # Supplemental Symbols and Pictographs
            r'[\U0001FA70-\U0001FAFF]',  # Symbols and Pictographs Extended-A
            # Дополнительные символы
            r'[🔥⚡️💥🚨⚠️❗️❌✅👍👎💯🎯📢📣🔔]',
            # Специальные символы для новостей
            r'[→←↑↓↗↘]',
            r'[★☆⭐]',
            r'[💬💭💡]'
        ]
        
        # Паттерны для ссылок (оставляем только основные домены)
        self.link_patterns = [
            r'https?://[^\s]+',  # HTTP/HTTPS ссылки
            r'www\.[^\s]+',     # WWW ссылки
            r'[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?'  # Общие домены
        ]
        
        # Разрешенные домены (не удаляем)
        self.allowed_domains = [
            'ria.ru', 'lenta.ru', 'rbc.ru', 'gazeta.ru', 'kommersant.ru',
            'tsn.ua', 'unian.ua', 'rt.com', '7kanal.co.il', 'cnn.com',
            'aljazeera.com', 'reuters.com', 'france24.com', 'dw.com',
            'euronews.com', 'bbc.com', 'bbc.co.uk'
        ]
        
        # Минимальные требования к контенту
        self.min_content_length = 100  # Минимальная длина контента
        self.min_title_length = 10     # Минимальная длина заголовка
        
    def validate_content(self, title: str, content: str) -> Tuple[bool, str, str]:
        """
        Валидирует контент новости
        
        Args:
            title: Заголовок новости
            content: Содержимое новости
            
        Returns:
            Tuple[bool, str, str]: (is_valid, cleaned_title, cleaned_content)
                - is_valid: True если контент валиден
                - cleaned_title: Очищенный заголовок
                - cleaned_content: Очищенное содержимое
        """
        try:
            # Проверяем на None и пустые строки
            if not title or not content:
                logger.warning("Пустой заголовок или контент")
                return False, "", ""
            
            # Очищаем контент
            cleaned_title = self._clean_text(title)
            cleaned_content = self._clean_text(content)
            
            # Проверяем минимальную длину
            if len(cleaned_title) < self.min_title_length:
                logger.warning(f"Заголовок слишком короткий: {len(cleaned_title)} символов")
                return False, cleaned_title, cleaned_content
                
            if len(cleaned_content) < self.min_content_length:
                logger.warning(f"Контент слишком короткий: {len(cleaned_content)} символов")
                return False, cleaned_title, cleaned_content
            
            # Проверяем на плохие фразы
            full_text = f"{cleaned_title} {cleaned_content}".lower()
            for phrase in self.bad_content_phrases:
                if phrase.lower() in full_text:
                    logger.warning(f"Найдена плохая фраза: '{phrase}'")
                    return False, cleaned_title, cleaned_content
            
            # Проверяем на слишком много эмодзи
            emoji_count = self._count_emojis(full_text)
            if emoji_count > 3:  # Максимум 3 эмодзи
                logger.warning(f"Слишком много эмодзи: {emoji_count}")
                return False, cleaned_title, cleaned_content
            
            # Проверяем на спам (повторяющиеся фразы)
            if self._is_spam(cleaned_content):
                logger.warning("Контент похож на спам")
                return False, cleaned_title, cleaned_content
            
            logger.info(f"Контент валиден: {len(cleaned_title)} символов в заголовке, {len(cleaned_content)} в контенте")
            return True, cleaned_title, cleaned_content
            
        except Exception as e:
            logger.error(f"Ошибка при валидации контента: {e}")
            return False, title, content
    
    def _clean_text(self, text: str) -> str:
        """
        Очищает текст от эмодзи, лишних ссылок и форматирования
        
        Args:
            text: Исходный текст
            
        Returns:
            str: Очищенный текст
        """
        if not text:
            return ""
        
        cleaned = text
        
        # Удаляем эмодзи
        for pattern in self.emoji_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.UNICODE)
        
        # Удаляем лишние ссылки (кроме разрешенных доменов)
        cleaned = self._remove_unwanted_links(cleaned)
        
        # Удаляем лишние пробелы и переносы строк
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Множественные пробелы в один
        cleaned = re.sub(r'\n+', '\n', cleaned)  # Множественные переносы в один
        
        # Удаляем HTML теги
        cleaned = re.sub(r'<[^>]+>', '', cleaned)
        
        # Удаляем лишние знаки препинания
        cleaned = re.sub(r'[!]{2,}', '!', cleaned)  # Множественные восклицательные знаки
        cleaned = re.sub(r'[?]{2,}', '?', cleaned)  # Множественные вопросительные знаки
        cleaned = re.sub(r'[.]{3,}', '...', cleaned)  # Множественные точки
        
        # Удаляем специальные символы для форматирования
        cleaned = re.sub(r'[_\*#]+', '', cleaned)  # Подчеркивания, звездочки, решетки
        
        return cleaned.strip()
    
    def _remove_unwanted_links(self, text: str) -> str:
        """
        Удаляет нежелательные ссылки, оставляя только разрешенные домены
        
        Args:
            text: Исходный текст
            
        Returns:
            str: Текст без нежелательных ссылок
        """
        cleaned = text
        
        # Находим все ссылки
        for pattern in self.link_patterns:
            links = re.findall(pattern, cleaned)
            for link in links:
                # Проверяем, является ли домен разрешенным
                is_allowed = any(domain in link.lower() for domain in self.allowed_domains)
                if not is_allowed:
                    # Удаляем нежелательную ссылку
                    cleaned = cleaned.replace(link, '')
        
        return cleaned
    
    def _count_emojis(self, text: str) -> int:
        """
        Подсчитывает количество эмодзи в тексте
        
        Args:
            text: Исходный текст
            
        Returns:
            int: Количество эмодзи
        """
        count = 0
        for pattern in self.emoji_patterns:
            matches = re.findall(pattern, text, flags=re.UNICODE)
            count += len(matches)
        return count
    
    def _is_spam(self, content: str) -> bool:
        """
        Проверяет, является ли контент спамом
        
        Args:
            content: Контент для проверки
            
        Returns:
            bool: True если контент похож на спам
        """
        # Проверяем на повторяющиеся фразы
        words = content.lower().split()
        if len(words) < 10:
            return False
        
        # Ищем повторяющиеся последовательности слов
        for i in range(len(words) - 5):
            phrase = ' '.join(words[i:i+5])
            if content.lower().count(phrase) > 2:
                return True
        
        # Проверяем на слишком много заглавных букв
        upper_ratio = sum(1 for c in content if c.isupper()) / len(content) if content else 0
        if upper_ratio > 0.3:  # Более 30% заглавных букв
            return True
        
        # Проверяем на слишком много восклицательных знаков
        exclamation_ratio = content.count('!') / len(content) if content else 0
        if exclamation_ratio > 0.05:  # Более 5% восклицательных знаков
            return True
        
        return False
    
    def get_validation_stats(self, title: str, content: str) -> dict:
        """
        Возвращает статистику валидации контента
        
        Args:
            title: Заголовок
            content: Контент
            
        Returns:
            dict: Статистика валидации
        """
        stats = {
            'title_length': len(title) if title else 0,
            'content_length': len(content) if content else 0,
            'emoji_count': self._count_emojis(f"{title} {content}"),
            'has_bad_phrases': False,
            'is_spam': False,
            'upper_ratio': 0.0,
            'exclamation_ratio': 0.0
        }
        
        if content:
            full_text = f"{title} {content}".lower()
            
            # Проверяем плохие фразы
            for phrase in self.bad_content_phrases:
                if phrase.lower() in full_text:
                    stats['has_bad_phrases'] = True
                    break
            
            # Проверяем спам
            stats['is_spam'] = self._is_spam(content)
            
            # Статистика символов
            stats['upper_ratio'] = sum(1 for c in content if c.isupper()) / len(content)
            stats['exclamation_ratio'] = content.count('!') / len(content)
        
        return stats


# Глобальный экземпляр валидатора
content_validator = ContentValidator()


def validate_news_content(title: str, content: str) -> Tuple[bool, str, str]:
    """
    Удобная функция для валидации контента новости
    
    Args:
        title: Заголовок новости
        content: Содержимое новости
        
    Returns:
        Tuple[bool, str, str]: (is_valid, cleaned_title, cleaned_content)
    """
    return content_validator.validate_content(title, content)


def get_content_stats(title: str, content: str) -> dict:
    """
    Удобная функция для получения статистики контента
    
    Args:
        title: Заголовок
        content: Контент
        
    Returns:
        dict: Статистика валидации
    """
    return content_validator.get_validation_stats(title, content)


if __name__ == "__main__":
    # Тестирование валидатора
    test_cases = [
        ("Нормальная новость", "Это обычная новость без проблем. Содержит достаточно текста для валидации."),
        ("Не удалось извлечь содержимое статьи", "Ошибка загрузки контента"),
        ("🔥 СРОЧНО! ⚡️", "ВАЖНАЯ НОВОСТЬ!!! Подпишитесь на наш канал!"),
        ("Короткая", "Мало текста"),
        ("Спам новость", "Повторяющаяся фраза повторяющаяся фраза повторяющаяся фраза повторяющаяся фраза")
    ]
    
    print("Тестирование ContentValidator:")
    print("=" * 50)
    
    for title, content in test_cases:
        is_valid, clean_title, clean_content = validate_news_content(title, content)
        stats = get_content_stats(title, content)
        
        print(f"Заголовок: {title}")
        print(f"Контент: {content}")
        print(f"Валиден: {is_valid}")
        print(f"Очищенный заголовок: {clean_title}")
        print(f"Очищенный контент: {clean_content}")
        print(f"Статистика: {stats}")
        print("-" * 30)
