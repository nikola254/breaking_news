# Структура проекта Breaking News

## Общая архитектура

```
breaking_news/
├── app/                      # Основное приложение
│   ├── blueprints/          # API и роуты
│   ├── static/              # Статические файлы
│   ├── templates/           # HTML шаблоны
│   └── utils/               # Вспомогательные модули
├── parsers/                 # Парсеры новостей
└── run.py                   # Точка входа
```

## Детальная структура

### /app - Основное приложение Flask

#### /app/blueprints - API эндпоинты и бизнес-логика

**1. ukraine_analytics_api.py** - Аналитика новостей
- `GET /api/ukraine_analytics/latest_news` - Получение последних новостей
- `GET /api/ukraine_analytics/statistics` - Статистика по новостям
- `GET /api/ukraine_analytics/tension_chart` - График динамики напряженности
- `GET /api/ukraine_analytics/category_chart` - График по категориям
- `GET /api/ukraine_analytics/sources_chart` - График по источникам
- **Взаимодействует с**: ClickHouse, TensionAnalyzer

**2. forecast_api.py** - Прогнозирование событий
- `POST /api/forecast/generate_forecast` - Генерация прогноза с AI
- Функции: `perform_real_analysis()`, `generate_ai_forecast()`, `calculate_weighted_tension_from_articles()`
- **Взаимодействует с**: ClickHouse, GenApiNewsClassifier, chart_api

**3. chart_api.py** - Создание графиков
- `POST /api/charts/generate_charts` - Генерация графиков для прогноза
- Функции: `generate_tension_chart_from_data()`, `cleanup_old_charts()`
- **Взаимодействует с**: Matplotlib, файловая система

**4. social_analysis_api.py** - Анализ социальных сетей
- `GET /api/social_media/<source>` - Получение постов из соцсетей
- `POST /api/social_media/parse` - Парсинг соцсетей
- **Взаимодействует с**: ClickHouse, парсеры соцсетей

**5. other APIs** - Дополнительные эндпоинты
- `parser_api.py` - Управление парсерами новостей
- `database_api.py` - Работа с базой данных

#### /app/static - Статические файлы

**CSS:**
- `database.css` - Стили для страницы базы данных
- `predict.css` - Стили для страницы прогнозирования
- `social_analysis.css` - Стили для анализа соцсетей

**JavaScript:**
- `database.js` - Логика базы данных (поиск, фильтрация, модальные окна)
- `predict.js` - Логика прогнозирования (генерация прогноза, отображение графиков, markdown парсинг)
- `social_analysis.js` - Логика анализа соцсетей
- `main.js` - Общая логика (главная страница)

**Images:**
- Хранилище сгенерированных графиков
- Ограничение: 5 последних графиков каждого типа

#### /app/templates - HTML шаблоны

- `base.html` - Базовый шаблон
- `index.html` - Главная страница
- `database.html` - База данных новостей
- `predict.html` - Страница прогнозирования
- `social_analysis.html` - Анализ социальных сетей

#### /app/utils - Вспомогательные модули

**1. tension_analyzer.py** - Анализ социальной напряженности
- Класс `TensionAnalyzer`
- Методы: `analyze_text_tension()`, расчет индексов
- **Используется в**: ukraine_analytics_api, forecast_api

**2. ai_classifier.py** - AI классификация новостей
- Класс `GenApiNewsClassifier`
- Методы: `classify_news()`, `generate_forecast()`
- **Взаимодействует с**: GenAPI

**3. clickhouse_client.py** - Клиент базы данных
- Функция `get_clickhouse_client()`
- **Используется в**: все API модули

### /parsers - Парсеры новостей

**Структура парсеров:**
- `ria_parser.py` - РИА Новости
- `bbc_parser.py` - BBC
- `cnn_parser.py` - CNN
- `telegram_parser.py` - Telegram каналы
- и т.д. (17+ источников)

**Базовый класс:** `BaseParser`
- Методы: `parse()`, `save_to_db()`, `analyze_tension()`
- **Взаимодействует с**: ClickHouse, TensionAnalyzer

### Поток данных

#### 1. Парсинг новостей
```
User → parser_api.py → Парсер → ClickHouse
                              ↓
                         TensionAnalyzer (расчет напряженности)
```

#### 2. Просмотр базы данных
```
User → database.html → database.js → ukraine_analytics_api.py → ClickHouse
                                                               ↓
                                                          JSON ответ
```

#### 3. Генерация прогноза
```
User → predict.html → predict.js → forecast_api.py → ClickHouse (данные)
                                                   ↓
                                          GenApiNewsClassifier (AI)
                                                   ↓
                                             chart_api.py (графики)
                                                   ↓
                                          JSON с прогнозом и графиками
```

#### 4. Поиск новостей
```
User вводит запрос → database.js → ukraine_analytics_api.py (с параметром search)
                                                            ↓
                                                      ClickHouse (фильтрация)
                                                            ↓
                          database.js (выделение, сортировка по релевантности)
```

## Ключевые функции

### Расчет социальной напряженности

**calculate_weighted_tension_from_articles()** в forecast_api.py:
- Собирает значения `social_tension_index` из всех статей
- Применяет экспоненциальное затухание по дате: `weight = exp(-days_ago * 0.1)`
- Возвращает взвешенное среднее для передачи в AI

### Markdown парсинг

**parseMarkdown()** в predict.js:
- Преобразует markdown символы в HTML
- Поддерживает: заголовки (h1-h5), жирный текст, курсив, списки
- Используется для отображения AI ответов

### Очистка старых графиков

**cleanup_old_charts()** в chart_api.py:
- Сохраняет только последние 5 графиков каждого типа
- Вызывается автоматически после сохранения нового графика
- Освобождает место на диске

### Поиск и фильтрация

**filterSearchResults()** в database.js:
- Подсчет релевантности: заголовок (вес 3) + контент (вес 1)
- Сортировка по релевантности
- Отображение количества найденных статей

## База данных ClickHouse

### Таблицы

Все таблицы находятся в схеме `news`:
- `ria_headlines`, `bbc_headlines`, `cnn_headlines` и т.д.
- Поля: `title`, `content`, `published_date`, `category`, `source`, `social_tension_index`, `spike_index`

### Индексы

- Первичный ключ: `published_date`
- Индексы для фильтрации по категориям и источникам

## Конфигурация

- **ClickHouse**: настройки подключения в `app/utils/clickhouse_client.py`
- **AI API**: ключи в переменных окружения или конфиге
- **Парсеры**: настройки в каждом парсере отдельно

## Разработка

### Добавление нового источника новостей

1. Создать файл парсера в `/parsers/new_source_parser.py`
2. Наследоваться от `BaseParser`
3. Реализовать метод `parse()`
4. Добавить в `parser_api.py`

### Добавление нового типа графика

1. Создать функцию в `chart_api.py`
2. Добавить вызов `cleanup_old_charts()` с соответствующим префиксом
3. Вернуть URL графика

### Изменение AI модели

Обновить класс `GenApiNewsClassifier` в `app/utils/ai_classifier.py`
