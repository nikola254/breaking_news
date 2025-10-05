"""
Модуль для проверки дубликатов статей в базе данных
Использует несколько методов:
1. Проверка по точному совпадению URL
2. Проверка по схожести заголовков (Levenshtein distance)
3. Проверка по хешу содержимого
"""
import hashlib
from difflib import SequenceMatcher
from typing import Optional, Tuple
from datetime import datetime, timedelta
import sys
import os

# Добавляем путь к корневой директории проекта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clickhouse_driver import Client
from config import Config


def get_clickhouse_client():
    """Получение клиента ClickHouse"""
    return Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=Config.CLICKHOUSE_DATABASE
    )


class DuplicateChecker:
    """Класс для проверки дубликатов статей"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        """
        Args:
            similarity_threshold: Порог схожести заголовков (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.client = None
    
    def __enter__(self):
        """Контекстный менеджер - открываем соединение с БД"""
        self.client = get_clickhouse_client()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрываем соединение с БД"""
        if self.client:
            self.client.close()
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Вычисляет схожесть двух текстов (0-1)
        
        Args:
            text1: Первый текст
            text2: Второй текст
            
        Returns:
            Коэффициент схожести от 0 до 1
        """
        if not text1 or not text2:
            return 0.0
        
        # Нормализуем тексты
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        # Используем SequenceMatcher для вычисления схожести
        return SequenceMatcher(None, t1, t2).ratio()
    
    def _calculate_content_hash(self, title: str, content: str) -> str:
        """
        Вычисляет хеш контента (заголовок + содержимое)
        
        Args:
            title: Заголовок статьи
            content: Содержимое статьи
            
        Returns:
            SHA256 хеш строки
        """
        combined = f"{title.lower().strip()}{content.lower().strip()}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()
    
    def check_by_link(self, link: str, table_name: str) -> bool:
        """
        Проверяет наличие статьи по URL
        
        Args:
            link: URL статьи
            table_name: Название таблицы для проверки
            
        Returns:
            True если дубликат найден, False иначе
        """
        if not link or not self.client:
            return False
        
        try:
            query = f"""
            SELECT count(*) as cnt
            FROM news.{table_name}
            WHERE link = %(link)s
            """
            
            result = self.client.execute(query, {'link': link})
            return result[0][0] > 0
            
        except Exception as e:
            print(f"Ошибка проверки по ссылке: {e}")
            return False
    
    def check_by_title_similarity(
        self,
        title: str,
        table_name: str,
        days_back: int = 7
    ) -> Tuple[bool, Optional[str]]:
        """
        Проверяет наличие похожей статьи по заголовку
        
        Args:
            title: Заголовок статьи
            table_name: Название таблицы для проверки
            days_back: Сколько дней назад искать (по умолчанию 7)
            
        Returns:
            Tuple (is_duplicate, similar_title)
        """
        if not title or not self.client:
            return False, None
        
        try:
            # Получаем последние заголовки за N дней
            query = f"""
            SELECT title
            FROM news.{table_name}
            WHERE published_date >= now() - INTERVAL {days_back} DAY
            ORDER BY published_date DESC
            LIMIT 1000
            """
            
            results = self.client.execute(query)
            
            # Проверяем схожесть с каждым заголовком
            for (existing_title,) in results:
                similarity = self._calculate_text_similarity(title, existing_title)
                
                if similarity >= self.similarity_threshold:
                    return True, existing_title
            
            return False, None
            
        except Exception as e:
            print(f"Ошибка проверки по заголовку: {e}")
            return False, None
    
    def check_by_content_hash(
        self,
        title: str,
        content: str,
        table_name: str,
        days_back: int = 7
    ) -> bool:
        """
        Проверяет наличие статьи по хешу содержимого
        
        Args:
            title: Заголовок статьи
            content: Содержимое статьи
            table_name: Название таблицы для проверки
            days_back: Сколько дней назад искать
            
        Returns:
            True если дубликат найден, False иначе
        """
        if not title or not content or not self.client:
            return False
        
        try:
            content_hash = self._calculate_content_hash(title, content)
            
            # Получаем хеши существующих статей
            query = f"""
            SELECT title, content
            FROM news.{table_name}
            WHERE published_date >= now() - INTERVAL {days_back} DAY
            LIMIT 1000
            """
            
            results = self.client.execute(query)
            
            for (existing_title, existing_content) in results:
                existing_hash = self._calculate_content_hash(
                    existing_title,
                    existing_content or ""
                )
                
                if content_hash == existing_hash:
                    return True
            
            return False
            
        except Exception as e:
            print(f"Ошибка проверки по хешу: {e}")
            return False
    
    def is_duplicate(
        self,
        title: str,
        content: str,
        link: str,
        table_name: str,
        check_methods: list = ['link', 'title', 'content']
    ) -> Tuple[bool, str]:
        """
        Комплексная проверка на дубликаты
        
        Args:
            title: Заголовок статьи
            content: Содержимое статьи
            link: URL статьи
            table_name: Название таблицы для проверки
            check_methods: Методы проверки ['link', 'title', 'content']
            
        Returns:
            Tuple (is_duplicate, reason)
        """
        # Проверка по ссылке
        if 'link' in check_methods and link:
            if self.check_by_link(link, table_name):
                return True, "Дубликат по URL"
        
        # Проверка по заголовку
        if 'title' in check_methods and title:
            is_dup, similar_title = self.check_by_title_similarity(title, table_name)
            if is_dup:
                return True, f"Похожий заголовок: '{similar_title}'"
        
        # Проверка по содержимому
        if 'content' in check_methods and content:
            if self.check_by_content_hash(title, content, table_name):
                return True, "Дубликат по содержимому"
        
        return False, ""
    
    def get_duplicate_stats(self, table_name: str, days: int = 7) -> dict:
        """
        Получает статистику дубликатов в таблице
        
        Args:
            table_name: Название таблицы
            days: Период для анализа
            
        Returns:
            Словарь со статистикой
        """
        if not self.client:
            return {}
        
        try:
            # Ищем дубликаты по ссылкам
            query = f"""
            SELECT link, count(*) as cnt
            FROM news.{table_name}
            WHERE published_date >= now() - INTERVAL {days} DAY
                AND link != ''
            GROUP BY link
            HAVING cnt > 1
            """
            
            results = self.client.execute(query)
            
            return {
                'duplicates_by_link': len(results),
                'total_duplicate_articles': sum(cnt - 1 for _, cnt in results),
                'table': table_name,
                'period_days': days
            }
            
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {}


# Создаем глобальный экземпляр
def create_duplicate_checker(similarity_threshold: float = 0.85) -> DuplicateChecker:
    """Фабричная функция для создания проверщика дубликатов"""
    return DuplicateChecker(similarity_threshold)


if __name__ == '__main__':
    # Тестирование
    print("Тестирование модуля проверки дубликатов...")
    
    with create_duplicate_checker() as checker:
        # Пример проверки
        is_dup, reason = checker.is_duplicate(
            title="Тестовая новость",
            content="Содержимое тестовой новости",
            link="https://example.com/test",
            table_name="lenta_headlines"
        )
        
        print(f"Дубликат: {is_dup}")
        if is_dup:
            print(f"Причина: {reason}")
        
        # Статистика
        stats = checker.get_duplicate_stats("lenta_headlines", days=7)
        print(f"\nСтатистика дубликатов: {stats}")

