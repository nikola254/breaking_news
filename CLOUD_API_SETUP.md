# Настройка Cloud.ru API для анализа экстремизма

## 📋 Обзор

Система автоматически использует API ключ Cloud.ru Foundation Models из файла `.env` для определения процента экстремизма в текстах.

## ⚙️ Конфигурация

### Файл .env
API ключ уже настроен в файле `.env`:
```env
API_KEY=ZTFlZTgwNGEtZDk0Mi00ZjY2LWI3NmMtZmYzMjdiZDJjYmQ3.606f5e53b3f31fa83a54c7d2da40e0d9
CLOUD_RU_API_KEY=ZTFlZTgwNGEtZDk0Mi00ZjY2LWI3NmMtZmYzMjdiZDJjYmQ3.606f5e53b3f31fa83a54c7d2da40e0d9
```

### Автоматическая загрузка
Система автоматически загружает настройки из `.env` файла через `config.py`:

```python
# config.py
CLOUD_RU_API_KEY = os.environ.get('CLOUD_RU_API_KEY') or os.environ.get('API_KEY')
CLOUD_MODEL_URL = os.environ.get('CLOUD_MODEL_URL', 'https://foundation-models.api.cloud.ru/v1/chat/completions')
CLOUD_MODEL_TOKEN = os.environ.get('CLOUD_MODEL_TOKEN') or os.environ.get('CLOUD_RU_API_KEY') or os.environ.get('API_KEY')
```

## 🚀 Использование

### ExtremistContentClassifier
Классификатор автоматически использует настройки из config.py:

```python
from app.ai.content_classifier import ExtremistContentClassifier

classifier = ExtremistContentClassifier()
result = classifier.analyze_extremism_percentage("Текст для анализа")

print(f"Процент экстремизма: {result['extremism_percentage']}%")
print(f"Уровень риска: {result['risk_level']}")
print(f"Метод анализа: {result['method']}")  # 'cloud_api' или 'local_fallback'
```

### Социальные сети
Все анализаторы социальных сетей (VK, Telegram, OK) автоматически используют облачную модель:

```python
from app.social_media.vk_api import VKAnalyzer

vk_analyzer = VKAnalyzer(access_token="your_token")
analyzed_posts = vk_analyzer.analyze_content_batch(posts, keywords)

# Каждый пост теперь содержит:
# - extremism_percentage: процент экстремизма (0-100%)
# - analysis_method: 'cloud_api' или 'local_fallback'
# - explanation: объяснение от облачной модели
```

## 📊 Результаты анализа

### Уровни риска
- **none** (0-19%): Безопасный контент
- **low** (20-39%): Низкий риск
- **medium** (40-59%): Средний риск  
- **high** (60-79%): Высокий риск
- **critical** (80-100%): Критический риск

### Социальные факторы
Система учитывает дополнительные факторы для социальных сетей:
- **VK**: репосты, комментарии, длина текста
- **Telegram**: просмотры, пересылки, ответы, медиа, ссылки
- **OK**: лайки, комментарии, вложения

## 🔄 Fallback система

Если облачная модель недоступна, система автоматически переключается на локальный анализ:
- Используются правила и ключевые слова
- Машинное обучение (если модель обучена)
- Результат помечается как `method: 'local_fallback'`

## ✅ Проверка работы

Система логирует статус конфигурации при инициализации:
- `"Cloud model configured successfully"` - облачная модель настроена
- `"Cloud model not configured - using local analysis only"` - используется только локальный анализ

## 🎯 Преимущества

1. **Автоматическая настройка** - не нужно устанавливать переменные окружения
2. **Высокая точность** - использует современную языковую модель
3. **Надежность** - fallback к локальному анализу
4. **Процентная оценка** - точное определение уровня экстремизма
5. **Контекстный анализ** - учитывает семантику и контекст