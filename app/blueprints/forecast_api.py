"""API для прогнозирования и анализа трендов новостей.

Этот модуль содержит функции для:
- Генерации прогнозов напряженности новостей
- Анализа трендов по категориям
- Создания визуализаций данных
- Статистического анализа новостных потоков
"""

from flask import Blueprint, request, jsonify, current_app
import datetime
import random
import os
import matplotlib
matplotlib.use('Agg')  # Используем не-интерактивный бэкенд
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import uuid
from clickhouse_driver import Client
from config import Config
from textblob import TextBlob
import re
from collections import Counter

# Создаем Blueprint для API прогнозов
forecast_api_bp = Blueprint('forecast_api', __name__, url_prefix='/api')

def get_clickhouse_client():
    """Создание клиента для подключения к ClickHouse.
    
    Returns:
        Client: Настроенный клиент ClickHouse
    """
    return Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=current_app.config.get('CLICKHOUSE_DB', 'default')
    )

def get_clickhouse_connection():
    """Получение соединения с ClickHouse"""
    try:
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            database=current_app.config.get('CLICKHOUSE_DB', 'default')
        )
        return client
    except Exception as e:
        print(f"Ошибка подключения к ClickHouse: {e}")
        return None

def get_military_keywords():
    """Военные ключевые слова для анализа"""
    return {
        'military_operations': ['наступление', 'атака', 'операция', 'штурм', 'удар', 'бомбардировка', 'обстрел'],
        'weapons': ['танк', 'артиллерия', 'ракета', 'дрон', 'авиация', 'вертолет', 'истребитель'],
        'locations': ['фронт', 'позиция', 'укрепление', 'база', 'аэродром', 'склад', 'мост'],
        'personnel': ['солдат', 'офицер', 'генерал', 'командир', 'военный', 'боец'],
        'escalation': ['мобилизация', 'призыв', 'резерв', 'подкрепление', 'эскалация']
    }

def analyze_sentiment(text):
    """Анализ тональности текста"""
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            return 'positive'
        elif polarity < -0.1:
            return 'negative'
        else:
            return 'neutral'
    except:
        return 'neutral'

def calculate_tension_index(news_data, military_keywords):
    """Расчет индекса напряженности"""
    if not news_data:
        return 0.5
    
    tension_score = 0
    total_weight = 0
    
    for article in news_data:
        text = (article.get('title', '') + ' ' + article.get('content', '')).lower()
        
        # Подсчет военных ключевых слов
        military_count = 0
        for category, keywords in military_keywords.items():
            for keyword in keywords:
                military_count += text.count(keyword)
        
        # Анализ тональности
        sentiment = analyze_sentiment(text)
        sentiment_weight = {'negative': 1.0, 'neutral': 0.5, 'positive': 0.2}[sentiment]
        
        # Расчет веса статьи
        article_weight = 1 + (military_count * 0.1)
        
        # Базовый уровень напряженности
        base_tension = 0.3 + (military_count * 0.05)
        article_tension = min(1.0, base_tension * sentiment_weight)
        
        tension_score += article_tension * article_weight
        total_weight += article_weight
    
    return min(1.0, tension_score / total_weight if total_weight > 0 else 0.5)

def extract_key_topics(news_data, limit=10):
    """Извлечение ключевых тем"""
    if not news_data:
        return []
    
    # Объединяем все тексты
    all_text = ' '.join([article.get('title', '') + ' ' + article.get('content', '') for article in news_data])
    
    # Простое извлечение ключевых слов
    words = re.findall(r'\b[а-яё]{4,}\b', all_text.lower())
    
    # Исключаем стоп-слова
    stop_words = {'который', 'которая', 'которые', 'также', 'более', 'может', 'должен', 'после', 'время'}
    words = [word for word in words if word not in stop_words]
    
    # Подсчитываем частоту
    word_counts = Counter(words)
    
    # Возвращаем топ тем с весами
    topics = []
    for word, count in word_counts.most_common(limit):
        weight = min(1.0, count / len(news_data))
        topics.append({'topic': word, 'weight': weight})
    
    return topics

def generate_military_forecast(category, tension_index, topics, forecast_days):
    """Генерация военного прогноза"""
    if category not in ['ukraine', 'middle_east'] or tension_index < 0.6:
        return None
    
    # Определяем вероятные направления
    directions = {
        'ukraine': ['Харьковское', 'Запорожское', 'Херсонское', 'Донецкое'],
        'middle_east': ['Газа', 'Западный берег', 'Ливан', 'Сирия']
    }
    
    # Генерируем прогноз на основе уровня напряженности
    forecast = {
        'overall_assessment': {
            'tension_level': 'высокий' if tension_index > 0.8 else 'средний',
            'probability_escalation': min(95, int(tension_index * 100)),
            'risk_level': 'критический' if tension_index > 0.9 else 'повышенный'
        },
        'probable_actions': [],
        'risk_areas': directions.get(category, [])[:3],
        'timeline': {
            'short_term': f'1-{min(7, forecast_days)} дней',
            'medium_term': f'{min(7, forecast_days)}-{min(30, forecast_days)} дней'
        },
        'recommendations': [
            'Усиление мониторинга ситуации',
            'Подготовка к возможной эскалации',
            'Координация с союзниками'
        ]
    }
    
    # Добавляем вероятные действия на основе тем
    if any('наступление' in topic['topic'] for topic in topics):
        forecast['probable_actions'].append('Подготовка наступательных операций')
    if any('оборона' in topic['topic'] for topic in topics):
        forecast['probable_actions'].append('Укрепление оборонительных позиций')
    if any('авиация' in topic['topic'] for topic in topics):
        forecast['probable_actions'].append('Активизация авиационных ударов')
    
    return forecast

def perform_real_analysis(category, analysis_period, forecast_period):
    """Выполнение реального анализа данных"""
    try:
        client = get_clickhouse_connection()
        if not client:
            return None
        
        # Получаем список пользовательских таблиц
        custom_tables_query = """
            SELECT name 
            FROM system.tables 
            WHERE database = 'news' 
            AND name LIKE 'custom_%_headlines'
        """
        custom_tables = client.query(custom_tables_query)
        custom_unions = []
        
        for table in custom_tables.result_rows:
            table_name = table[0]
            custom_unions.append(f"SELECT title, content, parsed_date, category FROM news.{table_name}")
        
        # Формируем запрос в зависимости от категории
        if category == 'all':
            category_filter = ""
        else:
            category_filter = f"AND category = '{category}'"
        
        # Получаем данные за период анализа из всех таблиц
        # Формируем список всех таблиц (стандартные + пользовательские)
        all_unions = [
            "SELECT title, content, parsed_date, category FROM news.ria_headlines",
            "SELECT title, content, parsed_date, category FROM news.bbc_headlines",
            "SELECT title, content, parsed_date, category FROM news.cnn_headlines",
            "SELECT title, content, parsed_date, category FROM news.reuters_headlines",
            "SELECT title, content, parsed_date, category FROM news.france24_headlines",
            "SELECT title, content, parsed_date, category FROM news.aljazeera_headlines",
            "SELECT title, content, parsed_date, category FROM news.euronews_headlines",
            "SELECT title, content, parsed_date, category FROM news.dw_headlines",
            "SELECT title, content, parsed_date, category FROM news.rt_headlines",
            "SELECT title, content, parsed_date, category FROM news.gazeta_headlines",
            "SELECT title, content, parsed_date, category FROM news.lenta_headlines",
            "SELECT title, content, parsed_date, category FROM news.kommersant_headlines",
            "SELECT title, content, parsed_date, category FROM news.rbc_headlines",
            "SELECT title, content, parsed_date, category FROM news.tsn_headlines",
            "SELECT title, content, parsed_date, category FROM news.unian_headlines",
            "SELECT title, content, parsed_date, category FROM news.israil_headlines",
            "SELECT title, content, parsed_date, category FROM news.telegram_headlines"
        ]
        
        # Добавляем пользовательские таблицы
        all_unions.extend(custom_unions)
        
        query = f"""
        SELECT title, content, parsed_date as published_date, category
        FROM (
            {' UNION ALL '.join(all_unions)}
        ) as all_news
        WHERE parsed_date >= now() - INTERVAL {analysis_period} HOUR
        {category_filter}
        ORDER BY published_date DESC
        LIMIT 1000
        """
        
        news_data = client.query(query)
        
        if not news_data.result_rows:
            return None
        
        # Преобразуем в список словарей
        articles = []
        for row in news_data.result_rows:
            articles.append({
                'title': row[0],
                'content': row[1],
                'published_date': row[2],
                'category': row[3]
            })
        
        # Анализируем данные
        military_keywords = get_military_keywords()
        tension_index = calculate_tension_index(articles, military_keywords)
        topics = extract_key_topics(articles)
        
        # Генерируем прогноз напряженности
        forecast_days = max(1, forecast_period // 24)
        today = datetime.datetime.now()
        tension_values = []
        
        # Прогнозируем изменение напряженности
        base_trend = (tension_index - 0.5) * 0.1  # Тренд на основе текущего уровня
        
        for i in range(forecast_days):
            date = today + datetime.timedelta(days=i)
            
            # Добавляем случайные колебания и тренд
            daily_variation = np.random.normal(0, 0.03)
            trend_component = base_trend * (i / forecast_days)
            
            predicted_tension = tension_index + trend_component + daily_variation
            predicted_tension = max(0.1, min(1.0, predicted_tension))
            
            # Доверительные интервалы
            confidence = 0.95 - (i * 0.02)  # Уменьшаем уверенность со временем
            margin = (1 - confidence) * 0.2
            
            tension_values.append({
                'date': date.strftime('%d.%m.%Y'),
                'value': predicted_tension,
                'lower_bound': max(0.1, predicted_tension - margin),
                'upper_bound': min(1.0, predicted_tension + margin)
            })
        
        # Генерируем военный прогноз если применимо
        military_forecast = generate_military_forecast(category, tension_index, topics, forecast_days)
        
        return {
            'news_count': len(articles),
            'tension_index': tension_index,
            'tension_forecast': {
                'values': tension_values,
                'trend': 'растущий' if base_trend > 0 else 'снижающийся' if base_trend < 0 else 'стабильный'
            },
            'topics_forecast': {
                'topics': topics,
                'analysis_period': f'{analysis_period} часов'
            },
            'military_forecast': military_forecast
        }
        
    except Exception as e:
        print(f"Ошибка анализа: {e}")
        return None

def generate_fallback_topics(category):
    """Генерация тем по умолчанию для категории"""
    topics_by_category = {
        'ukraine': [
            {'topic': 'военные действия', 'weight': 0.8},
            {'topic': 'дипломатия', 'weight': 0.6},
            {'topic': 'гуманитарная помощь', 'weight': 0.4}
        ],
        'middle_east': [
            {'topic': 'конфликт', 'weight': 0.9},
            {'topic': 'переговоры', 'weight': 0.5},
            {'topic': 'беженцы', 'weight': 0.7}
        ],
        'all': [
            {'topic': 'политика', 'weight': 0.7},
            {'topic': 'экономика', 'weight': 0.6},
            {'topic': 'международные отношения', 'weight': 0.5}
        ]
    }
    
    return topics_by_category.get(category, topics_by_category['all'])

@forecast_api_bp.route('/generate_forecast', methods=['POST'])
def generate_forecast():
    """Генерация прогноза напряженности новостей.
    
    Анализирует исторические данные и создает прогноз
    напряженности новостей на указанный период.
    
    Request JSON:
        category (str): Категория новостей для анализа
        analysis_period (int): Период анализа в часах
        forecast_period (int): Период прогноза в часах
    
    Returns:
        JSON: Прогноз с данными и путем к графику
    """
    try:
        data = request.json
        category = data.get('category', 'all')
        analysis_period = data.get('analysis_period', 24)  # в часах
        forecast_period = data.get('forecast_period', 24)  # в часах
        
        # Преобразуем период прогноза в дни для совместимости с текущим кодом
        forecast_days = max(1, forecast_period // 24)
        
        # Используем реальный анализ данных из ClickHouse
        analysis_result = perform_real_analysis(category, analysis_period, forecast_period)
        
        if analysis_result:
            tension_values = analysis_result['tension_forecast']['values']
            topics_data = analysis_result['topics_forecast']['topics']
            military_forecast = analysis_result.get('military_forecast')
        else:
            # Fallback к генерации данных, если анализ не удался
            today = datetime.datetime.now()
            tension_values = []
            
            # Базовый уровень напряженности в зависимости от категории
            base_tension = {
                'all': 0.5,
                'ukraine': 0.7,
                'middle_east': 0.8,
                'fake_news': 0.4,
                'info_war': 0.6,
                'europe': 0.5,
                'usa': 0.55,
                'other': 0.3
            }.get(category, 0.5)
            
            # Генерируем значения с трендом
            trend = random.uniform(-0.1, 0.1)  # Случайный тренд
            
            for i in range(forecast_days):
                date = today + datetime.timedelta(days=i)
                # Добавляем случайные колебания и тренд
                noise = random.uniform(-0.05, 0.05)
                trend_component = trend * i / forecast_days
                value = min(1.0, max(0.1, base_tension + noise + trend_component))
                
                tension_values.append({
                    'date': date.strftime('%d.%m.%Y'),
                    'value': value,
                    'lower_bound': max(0.1, value - random.uniform(0.03, 0.08)),
                    'upper_bound': min(1.0, value + random.uniform(0.03, 0.08))
                })
            
            topics_data = generate_fallback_topics(category)
            military_forecast = None
        
        # Используем данные из реального анализа или fallback
        if not analysis_result:
            topics_data = generate_fallback_topics(category)
        
        # Темы в зависимости от категории
        topics_by_category = {
            'ukraine': [
                {'name': 'Военные действия', 'value': random.uniform(0.4, 0.6), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Дипломатия', 'value': random.uniform(0.2, 0.3), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Гуманитарная ситуация', 'value': random.uniform(0.1, 0.2), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Экономика', 'value': random.uniform(0.05, 0.15), 'change': random.uniform(-0.05, 0.05)},
                {'name': 'Другое', 'value': random.uniform(0.05, 0.1), 'change': random.uniform(-0.05, 0.05)}
            ],
            'middle_east': [
                {'name': 'Конфликт Израиль-Палестина', 'value': random.uniform(0.3, 0.5), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Иран', 'value': random.uniform(0.2, 0.3), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Сирия', 'value': random.uniform(0.1, 0.2), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Йемен', 'value': random.uniform(0.05, 0.15), 'change': random.uniform(-0.05, 0.05)},
                {'name': 'Другое', 'value': random.uniform(0.05, 0.1), 'change': random.uniform(-0.05, 0.05)}
            ],
            'fake_news': [
                {'name': 'Дезинформация', 'value': random.uniform(0.3, 0.5), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Манипуляции', 'value': random.uniform(0.2, 0.4), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Фейковые аккаунты', 'value': random.uniform(0.1, 0.2), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Другое', 'value': random.uniform(0.05, 0.15), 'change': random.uniform(-0.05, 0.05)}
            ]
        }
        
        # Для остальных категорий используем общие темы
        default_topics = [
            {'name': 'Политика', 'value': random.uniform(0.2, 0.4), 'change': random.uniform(-0.1, 0.1)},
            {'name': 'Экономика', 'value': random.uniform(0.1, 0.3), 'change': random.uniform(-0.1, 0.1)},
            {'name': 'Военные действия', 'value': random.uniform(0.2, 0.5), 'change': random.uniform(-0.1, 0.1)},
            {'name': 'Международные отношения', 'value': random.uniform(0.1, 0.2), 'change': random.uniform(-0.1, 0.1)},
            {'name': 'Другое', 'value': random.uniform(0.05, 0.15), 'change': random.uniform(-0.05, 0.05)}
        ]
        
        topics = topics_by_category.get(category, default_topics)
        
        # Добавляем военный прогноз в ответ если он есть
        response_data = {
            'success': True,
            'forecast': {
                'tension': {
                    'values': tension_values,
                    'trend': analysis_result.get('tension_forecast', {}).get('trend', 'стабильный') if analysis_result else 'неопределенный'
                },
                'topics': topics_data,
                'metadata': {
                    'category': category,
                    'analysis_period': f'{analysis_period} часов',
                    'forecast_period': f'{forecast_period} часов',
                    'news_analyzed': analysis_result.get('news_count', 0) if analysis_result else 0,
                    'tension_index': round(analysis_result.get('tension_index', 0.5) if analysis_result else 0.5, 3)
                }
            }
        }
        
        # Добавляем военный прогноз если он есть
        if analysis_result and analysis_result.get('military_forecast'):
            response_data['forecast']['military_forecast'] = analysis_result['military_forecast']
        
        return jsonify(response_data)
    except Exception as e:
        current_app.logger.error(f"Error generating forecast: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Функция для генерации графика прогноза напряженности
def generate_tension_chart(tension_values, category):
    plt.figure(figsize=(10, 6))
    sns.set_style("whitegrid")
    
    dates = [item['date'] for item in tension_values]
    values = [item['value'] for item in tension_values]
    lower_bounds = [item['lower_bound'] for item in tension_values]
    upper_bounds = [item['upper_bound'] for item in tension_values]
    
    plt.plot(dates, values, marker='o', linewidth=2, color='#1976D2', label='Индекс напряженности')
    plt.fill_between(dates, lower_bounds, upper_bounds, color='#1976D2', alpha=0.2, label='Диапазон прогноза')
    
    plt.title(f'Прогноз индекса социальной напряженности: {get_category_name(category)}')
    plt.xlabel('Дата')
    plt.ylabel('Индекс напряженности')
    plt.ylim(0, 1)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.legend()
    
    # Сохраняем график
    unique_id = uuid.uuid4().hex[:8]
    today_str = datetime.datetime.now().strftime('%Y%m%d')
    filename = f'tension_forecast_{category}_{today_str}_{unique_id}.png'
    
    static_folder = os.path.join(current_app.root_path, 'static', 'images')
    os.makedirs(static_folder, exist_ok=True)
    
    filepath = os.path.join(static_folder, filename)
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()
    
    return f'/static/images/{filename}'

# Функция для генерации графика распределения тем
def generate_topics_chart(topics, category):
    plt.figure(figsize=(10, 6))
    sns.set_style("whitegrid")
    
    names = [item['name'] for item in topics]
    values = [item['value'] for item in topics]
    changes = [item['change'] for item in topics]
    
    # Цвета в зависимости от изменения (красный - негативное, зеленый - позитивное)
    colors = ['#4CAF50' if change >= 0 else '#F44336' for change in changes]
    
    bars = plt.bar(names, values, color=colors)
    
    # Добавляем аннотации с процентами и изменениями
    for i, bar in enumerate(bars):
        height = bar.get_height()
        change = changes[i]
        change_symbol = '↑' if change > 0 else '↓' if change < 0 else '→'
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{values[i]:.1%}\n{change_symbol}{abs(change):.1%}',
                ha='center', va='bottom', fontsize=9)
    
    plt.title(f'Распределение тем: {get_category_name(category)}')
    plt.xlabel('Темы')
    plt.ylabel('Доля')
    plt.ylim(0, max(values) * 1.3)  # Оставляем место для аннотаций
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Сохраняем график
    unique_id = uuid.uuid4().hex[:8]
    today_str = datetime.datetime.now().strftime('%Y%m%d')
    filename = f'topics_forecast_{category}_{today_str}_{unique_id}.png'
    
    static_folder = os.path.join(current_app.root_path, 'static', 'images')
    os.makedirs(static_folder, exist_ok=True)
    
    filepath = os.path.join(static_folder, filename)
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()
    
    return f'/static/images/{filename}'

# Вспомогательная функция для получения читаемого названия категории
def get_category_name(category):
    categories = {
        'all': 'Все категории',
        'ukraine': 'Украина',
        'middle_east': 'Ближний восток',
        'fake_news': 'Фейки',
        'info_war': 'Инфовойна',
        'europe': 'Европа',
        'usa': 'США',
        'other': 'Другое'
    }
    return categories.get(category, category)