from flask import Blueprint, jsonify, request, current_app
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

# Создаем Blueprint для API прогнозов
forecast_api_bp = Blueprint('forecast_api', __name__, url_prefix='/api')

# Функция для получения клиента ClickHouse
def get_clickhouse_client():
    return Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=current_app.config.get('CLICKHOUSE_DB', 'default')
    )

# API-эндпоинт для генерации прогноза
@forecast_api_bp.route('/generate_forecast', methods=['POST'])
def generate_forecast():
    try:
        data = request.json
        category = data.get('category', 'all')
        analysis_period = data.get('analysis_period', 24)  # в часах
        forecast_period = data.get('forecast_period', 24)  # в часах
        
        # Преобразуем период прогноза в дни для совместимости с текущим кодом
        forecast_days = max(1, forecast_period // 24)
        
        # В реальном приложении здесь будет запрос к ClickHouse для получения данных
        # и вызов модели прогнозирования
        
        # Для демонстрации создадим более реалистичные данные на основе выбранных параметров
        
        # Генерируем случайные данные для примера, но с учетом выбранной категории
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
        
        # Генерируем графики
        tension_chart_path = generate_tension_chart(tension_values, category)
        topics_chart_path = generate_topics_chart(topics, category)
        
        # Формируем ответ
        response = {
            'status': 'success',
            'tension_forecast': {
                'chart_url': tension_chart_path,
                'values': tension_values
            },
            'topics_forecast': {
                'chart_url': topics_chart_path,
                'topics': topics
            }
        }
        
        return jsonify(response)
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
    
    static_folder = os.path.join(current_app.root_path, 'static', 'plots')
    os.makedirs(static_folder, exist_ok=True)
    
    filepath = os.path.join(static_folder, filename)
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()
    
    return f'/static/plots/{filename}'

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
    
    static_folder = os.path.join(current_app.root_path, 'static', 'plots')
    os.makedirs(static_folder, exist_ok=True)
    
    filepath = os.path.join(static_folder, filename)
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()
    
    return f'/static/plots/{filename}'

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