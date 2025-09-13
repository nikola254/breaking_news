import os
import logging
import requests
import json
from typing import Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AINewsClassifier:
    """Классификатор новостей с использованием нейросетевой модели"""
    
    def __init__(self):
        """Инициализация классификатора"""
        self.api_key = os.environ.get("API_KEY")
        self.base_url = "https://foundation-models.api.cloud.ru/v1"
        
        if not self.api_key:
            raise ValueError("API_KEY не найден в переменных окружения")
        
        # Используем requests напрямую вместо OpenAI клиента
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.api_url = f"{self.base_url}/chat/completions"
        
        # Определяем возможные категории
        self.categories = [
            'ukraine',      # Украина
            'middle_east',  # Ближний Восток
            'fake_news',    # Фейковые новости
            'info_war',     # Информационная война
            'europe',       # Европа
            'usa',          # США
            'other'         # Прочее
        ]
        
        logger.info("AINewsClassifier инициализирован")
    
    def classify_news(self, title: str, content: str) -> str:
        """Классифицирует новость по категориям с использованием ИИ
        
        Args:
            title (str): Заголовок новости
            content (str): Содержание новости
            
        Returns:
            str: Категория новости
        """
        try:
            # Проверяем входные данные на None
            if title is None:
                title = ""
            if content is None:
                content = ""
            
            # Формируем промпт для классификации
            prompt = self._create_classification_prompt(title, content)
            
            # Формируем данные для запроса
            data = {
                "model": "openai/gpt-oss-120b",
                "max_tokens": 100,
                "temperature": 0.1,
                "presence_penalty": 0,
                "top_p": 0.95,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Отправляем запрос
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"API вернул код {response.status_code}: {response.text}")
            
            # Парсим ответ
            response_data = response.json()
            raw_classification = response_data['choices'][0]['message']['content']
            
            # Проверяем на None и обрабатываем
            if raw_classification is None:
                logger.warning("API вернул None в качестве ответа")
                return 'other'
            
            classification = raw_classification.strip().lower()
            
            # Проверяем, что полученная категория валидна
            if classification in self.categories:
                logger.info(f"Статья классифицирована как: {classification}")
                return classification
            else:
                # Пытаемся найти категорию в ответе
                for category in self.categories:
                    if category in classification:
                        logger.info(f"Статья классифицирована как: {category}")
                        return category
                
                logger.warning(f"Неизвестная категория: {classification}, возвращаем 'other'")
                return 'other'
                
        except Exception as e:
            logger.error(f"Ошибка при классификации новости: {e}")
            return 'other'
    
    def _create_classification_prompt(self, title: str, content: str) -> str:
        """Создает промпт для классификации новости
        
        Args:
            title (str): Заголовок новости
            content (str): Содержание новости
            
        Returns:
            str: Промпт для ИИ
        """
        # Проверяем и обрабатываем None значения
        if title is None:
            title = ""
        if content is None:
            content = ""
        
        # Ограничиваем длину контента для экономии токенов
        max_content_length = 2000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""Классифицируй следующую новость по одной из категорий:

Категории:
- ukraine: новости о Украине, украинском конфликте, украинской политике
- middle_east: новости о Ближнем Востоке, Израиле, Палестине, Сирии, Иране
- fake_news: фейковые новости, дезинформация, пропаганда
- info_war: информационная война, кибератаки, влияние на общественное мнение
- europe: новости о Европе, ЕС, европейских странах
- usa: новости о США, американской политике
- other: все остальные новости

Заголовок: {title}

Содержание: {content}

Ответь только названием категории (одним словом):"""
        
        return prompt

# Функция для обратной совместимости с существующим кодом
def classify_news_ai(title: str, content: str) -> str:
    """Функция-обертка для классификации новостей через ИИ
    
    Args:
        title (str): Заголовок новости
        content (str): Содержание новости
        
    Returns:
        str: Категория новости
    """
    try:
        classifier = AINewsClassifier()
        return classifier.classify_news(title, content)
    except Exception as e:
        logger.error(f"Ошибка при создании классификатора: {e}")
        # Возвращаем fallback к старому методу
        from .news_categories import classify_news
        logger.info("Используем fallback к классификации по ключевым словам")
        return classify_news(title, content)

# Основная функция для тестирования
if __name__ == "__main__":
    # Тестовый пример
    test_title = "Украина получила новую военную помощь от США"
    test_content = "Соединенные Штаты объявили о предоставлении Украине дополнительного пакета военной помощи на сумму 2 миллиарда долларов. Пакет включает современные системы ПВО и артиллерийские снаряды."
    
    try:
        classifier = AINewsClassifier()
        result = classifier.classify_news(test_title, test_content)
        print(f"Результат классификации: {result}")
    except Exception as e:
        print(f"Ошибка: {e}")