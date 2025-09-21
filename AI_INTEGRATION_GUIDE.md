# Руководство по интеграции AI классификатора

Этот документ описывает, как интегрировать нейросетевую классификацию новостей в существующие парсеры.

## Обзор

В проекте теперь доступны два метода классификации:
1. **Классификация по ключевым словам** (существующий метод) - `news_categories.py`
2. **AI классификация** (новый метод) - `ai_news_classifier.py`

## Файлы проекта

### Основные файлы AI классификации
- `parsers/ai_news_classifier.py` - основной модуль AI классификации
- `test_ai_classifier.py` - тесты AI классификатора
- `test_cloud_api.py` - тест подключения к Cloud.ru API
- `parsers/parser_example_with_ai.py` - пример интеграции

### Конфигурация
- `.env` - содержит `API_KEY` для Cloud.ru Foundation Models API
- `requirements.txt` - обновлен с зависимостью `openai==1.54.4`

## Быстрый старт

### 1. Установка зависимостей
```bash
pip install openai==1.54.4
```

### 2. Настройка API ключа
Убедитесь, что в файле `.env` есть:
```
API_KEY=your_cloud_ru_api_key_here
```

### 3. Базовое использование
```python
from parsers.ai_news_classifier import classify_news_ai

# Классификация статьи
category = classify_news_ai(title="Заголовок новости", content="Содержимое статьи")
print(f"Категория: {category}")
```

## Интеграция в существующие парсеры

### Метод 1: Замена существующей классификации

```python
# Было:
from news_categories import classify_news
category = classify_news(title, content)

# Стало:
from parsers.ai_news_classifier import classify_news_ai
category = classify_news_ai(title, content)
```

### Метод 2: AI с fallback на ключевые слова (рекомендуется)

```python
from parsers.ai_news_classifier import classify_news_ai
from news_categories import classify_news

def classify_with_fallback(title, content):
    try:
        # Пробуем AI классификацию
        return classify_news_ai(title, content)
    except Exception as e:
        print(f"AI классификация не удалась: {e}")
        # Fallback на ключевые слова
        return classify_news(title, content)

category = classify_with_fallback(title, content)
```

### Метод 3: Гибридный подход с настройками

```python
import os
from parsers.ai_news_classifier import classify_news_ai
from news_categories import classify_news

def classify_news_hybrid(title, content, use_ai=None):
    """Гибридная классификация с возможностью выбора метода"""
    
    # Автоопределение доступности AI
    if use_ai is None:
        use_ai = os.getenv('API_KEY') is not None
    
    if use_ai:
        try:
            return classify_news_ai(title, content)
        except Exception:
            pass  # Fallback ниже
    
    return classify_news(title, content)
```

## Модификация конкретных парсеров

### parser_ria.py
```python
# Найти строку:
rubric = classify_news(title, content)

# Заменить на:
from parsers.ai_news_classifier import classify_news_ai
try:
    rubric = classify_news_ai(title, content)
except Exception as e:
    print(f"AI классификация не удалась: {e}")
    rubric = classify_news(title, content)
```

### parser_cnn.py
```python
# Найти строку:
rubric = classify_news(title, content)

# Заменить на:
from parsers.ai_news_classifier import classify_news_ai
try:
    rubric = classify_news_ai(title, content)
except Exception as e:
    print(f"AI классификация не удалась: {e}")
    rubric = classify_news(title, content)
```

## Категории классификации

AI классификатор поддерживает те же категории, что и классификация по ключевым словам:

- `ukraine` - новости об Украине
- `middle_east` - новости с Ближнего Востока
- `usa` - новости о США
- `europe` - новости о Европе
- `russia` - новости о России
- `china` - новости о Китае
- `info_war` - информационная война
- `fake_news` - фейковые новости
- `other` - прочие новости

## Мониторинг и логирование

### Добавление логирования классификации
```python
import logging

logger = logging.getLogger(__name__)

def classify_with_logging(title, content):
    try:
        category = classify_news_ai(title, content)
        logger.info(f"AI классификация: {category} для '{title[:50]}...'")
        return category
    except Exception as e:
        logger.warning(f"AI классификация не удалась: {e}")
        category = classify_news(title, content)
        logger.info(f"Fallback классификация: {category} для '{title[:50]}...'")
        return category
```

### Сбор статистики
```python
class ClassificationStats:
    def __init__(self):
        self.ai_success = 0
        self.ai_failures = 0
        self.keyword_used = 0
    
    def classify_and_track(self, title, content):
        try:
            category = classify_news_ai(title, content)
            self.ai_success += 1
            return category
        except Exception:
            self.ai_failures += 1
            category = classify_news(title, content)
            self.keyword_used += 1
            return category
    
    def get_stats(self):
        total = self.ai_success + self.ai_failures
        if total > 0:
            success_rate = (self.ai_success / total) * 100
            return f"AI успешность: {success_rate:.1f}% ({self.ai_success}/{total})"
        return "Нет данных"
```

## Тестирование

### Запуск тестов
```bash
# Тест AI классификатора
python test_ai_classifier.py

# Тест подключения к API
python test_cloud_api.py

# Пример интеграции
python parsers/parser_example_with_ai.py
```

### Ожидаемые результаты
- AI классификатор должен показывать точность 70%+
- Fallback на ключевые слова должен работать при сбоях AI
- Все категории должны корректно определяться

## Устранение неполадок

### Проблема: ModuleNotFoundError: No module named 'openai'
**Решение:** Установите зависимость
```bash
pip install openai==1.54.4
```

### Проблема: API ключ не найден
**Решение:** Проверьте файл `.env`
```bash
# Убедитесь, что есть строка:
API_KEY=your_api_key_here
```

### Проблема: Ошибки подключения к API
**Решение:** Проверьте доступность Cloud.ru API
```python
python test_cloud_api.py
```

### Проблема: Низкая точность классификации
**Решение:** 
1. Проверьте качество входных данных (title, content)
2. Убедитесь, что передается достаточно контекста
3. Рассмотрите настройку параметров модели

## Производительность

- **AI классификация:** ~2-5 секунд на статью
- **Классификация по ключевым словам:** ~0.01 секунды на статью
- **Рекомендация:** Используйте AI для важных статей, ключевые слова для массовой обработки

## Лучшие практики

1. **Всегда используйте fallback** на классификацию по ключевым словам
2. **Логируйте результаты** для мониторинга качества
3. **Ограничивайте длину контента** до 5000 символов для оптимальной работы
4. **Кэшируйте результаты** для повторно обрабатываемых статей
5. **Мониторьте использование API** для контроля расходов

## Дальнейшее развитие

- Добавление кэширования результатов классификации
- Настройка параметров модели для улучшения точности
- Интеграция с другими AI провайдерами для резервирования
- Автоматическое переключение между методами на основе нагрузки