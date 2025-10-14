# -*- coding: utf-8 -*-
"""
Модуль для создания графиков на основе данных прогноза от AI.

Этот модуль содержит функции для:
- Создания графиков напряженности на основе AI прогноза
- Создания графиков распределения тем
- Анализа данных от AI для извлечения числовых значений
"""

from flask import Blueprint, request, jsonify, current_app
import datetime
import os
import matplotlib
matplotlib.use('Agg')  # Используем не-интерактивный бэкенд
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import uuid

# Создаем Blueprint для API графиков
chart_api_bp = Blueprint('chart_api', __name__, url_prefix='/api/chart')

def get_category_name(category):
    """Получение читаемого названия категории.
    
    Args:
        category (str): Код категории
    
    Returns:
        str: Читаемое название категории
    """
    categories = {
        'all': 'Все категории',
        'military_operations': 'Военные операции',
        'humanitarian_crisis': 'Гуманитарный кризис',
        'economic_consequences': 'Экономические последствия',
        'political_decisions': 'Политические решения',
        'information_social': 'Информационно-социальные аспекты',
        'politics': 'Политика',
        'economy': 'Экономика', 
        'society': 'Общество',
        'technology': 'Технологии',
        'sports': 'Спорт',
        'culture': 'Культура',
        'health': 'Здоровье',
        'education': 'Образование',
        'environment': 'Экология',
        'crime': 'Криминал',
        'military': 'Военные действия',
        'international': 'Международные отношения',
        'humanitarian': 'Гуманитарная помощь'
    }
    return categories.get(category, category.title())

def create_empty_chart_simple(chart_type, category):
    """Создание пустого графика с сообщением об отсутствии данных."""
    try:
        plt.figure(figsize=(12, 8))
        plt.axis('off')
        
        message = f'Нет данных для категории "{get_category_name(category)}"'
        if chart_type == "tension":
            title = "График прогноза напряженности"
        else:
            title = "График распределения тем"
            
        plt.text(0.5, 0.6, message, ha='center', va='center', fontsize=16, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))
        plt.text(0.5, 0.4, title, ha='center', va='center', fontsize=18, fontweight='bold')
        
        # Сохраняем график
        unique_id = uuid.uuid4().hex[:8]
        today_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'empty_{chart_type}_{category}_{today_str}_{unique_id}.png'
        
        static_folder = os.path.join(current_app.root_path, 'static', 'images')
        os.makedirs(static_folder, exist_ok=True)
        
        filepath = os.path.join(static_folder, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return f'/static/images/{filename}'
        
    except Exception as e:
        current_app.logger.error(f"Error creating empty chart: {str(e)}")
        plt.close()
        return None

@chart_api_bp.route('/generate_charts', methods=['POST'])
def generate_charts():
    """Создание графиков на основе данных прогноза от AI.
    
    Request JSON:
        forecast_data (dict): Данные прогноза от AI
        category (str): Категория новостей
        ai_response (str): Полный ответ AI для дополнительного анализа
    
    Returns:
        JSON: Пути к созданным графикам
    """
    try:
        data = request.json
        forecast_data = data.get('forecast_data', {})
        category = data.get('category', 'all')
        ai_response = data.get('ai_response', '')
        
        # Создаем графики на основе данных прогноза
        tension_chart_url = None
        topics_chart_url = None
        
        # Создаем график напряженности, если есть данные
        if 'tension_forecast' in forecast_data and 'values' in forecast_data['tension_forecast']:
            tension_chart_url = generate_tension_chart_from_data(
                forecast_data['tension_forecast']['values'], 
                category
            )
        
        # Убираем генерацию графика тем - не нужен
        
        response = {
            'status': 'success',
            'tension_chart_url': tension_chart_url
        }
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error generating charts: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def generate_tension_chart_from_data(tension_values, category):
    """Создание графика напряженности на основе данных от AI.
    
    Args:
        tension_values (list): Список значений напряженности по дням
        category (str): Категория новостей
    
    Returns:
        str: Путь к созданному графику
    """
    try:
        # Проверка на пустые данные
        if not tension_values or len(tension_values) == 0:
            return create_empty_chart_simple("tension", category)
        
        # Логируем данные для отладки
        current_app.logger.info(f"Generating tension chart for category: {category}")
        current_app.logger.info(f"Tension values count: {len(tension_values) if tension_values else 0}")
        current_app.logger.info(f"Tension values sample: {tension_values[:2] if tension_values else 'None'}")
        
        plt.figure(figsize=(12, 7))
        sns.set_style("whitegrid")
        
        # Проверяем формат данных
        if isinstance(tension_values[0], dict):
            dates = [item.get('date', f'Day {i+1}') for i, item in enumerate(tension_values)]
            values = [item.get('value', 0) for item in tension_values]
            lower_bounds = [item.get('lower_bound', item.get('value', 0) - 0.05) for item in tension_values]
            upper_bounds = [item.get('upper_bound', item.get('value', 0) + 0.05) for item in tension_values]
        else:
            # Если данные приходят как простой список чисел
            dates = [f'Day {i+1}' for i in range(len(tension_values))]
            values = tension_values
            lower_bounds = [v - 0.05 for v in values]
            upper_bounds = [v + 0.05 for v in values]
        
        # Создаем график с улучшенным дизайном
        plt.plot(dates, values, marker='o', linewidth=3, color='#1976D2', 
                 label='Прогноз напряженности', markersize=8)
        plt.fill_between(dates, lower_bounds, upper_bounds, 
                         color='#1976D2', alpha=0.2, label='Диапазон неопределенности')
        
        # Добавляем аннотации с процентными значениями
        for i, (date, value) in enumerate(zip(dates, values)):
            plt.annotate(f'{value:.1%}', 
                        (i, value), 
                        textcoords="offset points", 
                        xytext=(0,10), 
                        ha='center', 
                        fontsize=9,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
        plt.title(f'Прогноз индекса социальной напряженности\n{get_category_name(category)}', 
                  fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Индекс напряженности', fontsize=12)
        plt.ylim(0, 1)
        
        # Улучшаем отображение дат
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.legend(loc='upper right')
        
        # Сохраняем график
        unique_id = uuid.uuid4().hex[:8]
        today_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'ai_tension_forecast_{category}_{today_str}_{unique_id}.png'
        
        static_folder = os.path.join(current_app.root_path, 'static', 'images')
        os.makedirs(static_folder, exist_ok=True)
        
        filepath = os.path.join(static_folder, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return f'/static/images/{filename}'
    
    except Exception as e:
        current_app.logger.error(f"Error generating tension chart: {str(e)}")
        plt.close()
        return create_empty_chart_simple("tension", category)

def generate_topics_chart_from_data(topics, category):
    """Создание графика распределения тем на основе данных от AI.
    
    Args:
        topics (list): Список тем с их значениями и изменениями
        category (str): Категория новостей
    
    Returns:
        str: Путь к созданному графику
    """
    try:
        # Проверка на пустые данные
        if not topics or len(topics) == 0:
            return create_empty_chart_simple("topics", category)
        
        # Логируем данные для отладки
        current_app.logger.info(f"Generating topics chart for category: {category}")
        current_app.logger.info(f"Topics count: {len(topics) if topics else 0}")
        current_app.logger.info(f"Topics sample: {topics[:2] if topics else 'None'}")
        
        plt.figure(figsize=(12, 8))
        sns.set_style("whitegrid")
        
        # Проверяем формат данных
        if isinstance(topics[0], dict):
            names = [item.get('name', f'Topic {i+1}') for i, item in enumerate(topics)]
            values = [item.get('value', item.get('weight', 0)) for item in topics]
            changes = [item.get('change', item.get('trend', 0)) for item in topics]
        else:
            # Если данные приходят в другом формате
            names = [str(topic) for topic in topics]
            values = [0.1] * len(topics)  # Значения по умолчанию
            changes = [0] * len(topics)
        
        # Цвета в зависимости от изменения (зеленый - рост, красный - падение, серый - стабильно)
        colors = []
        for change in changes:
            if change > 0.01:
                colors.append('#4CAF50')  # Зеленый для роста
            elif change < -0.01:
                colors.append('#F44336')  # Красный для падения
            else:
                colors.append('#9E9E9E')  # Серый для стабильности
        
        bars = plt.bar(names, values, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
        
        # Добавляем аннотации с процентами и изменениями
        for i, bar in enumerate(bars):
            height = bar.get_height()
            change = changes[i]
            
            # Определяем символ изменения
            if change > 0.01:
                change_symbol = '↗'
                change_color = '#4CAF50'
            elif change < -0.01:
                change_symbol = '↘'
                change_color = '#F44336'
            else:
                change_symbol = '→'
                change_color = '#9E9E9E'
            
            # Основная аннотация с процентом
            plt.text(bar.get_x() + bar.get_width()/2., height + max(values) * 0.02,
                    f'{values[i]:.1%}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
            
            # Аннотация с изменением
            plt.text(bar.get_x() + bar.get_width()/2., height + max(values) * 0.06,
                    f'{change_symbol} {abs(change):.1%}',
                    ha='center', va='bottom', fontsize=9, color=change_color, fontweight='bold')
        
        plt.title(f'Распределение тем по напряженности\n{get_category_name(category)}', 
                  fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Темы', fontsize=12)
        plt.ylabel('Доля в общей напряженности', fontsize=12)
        plt.ylim(0, max(values) * 1.4)  # Оставляем место для аннотаций
        
        # Улучшаем отображение названий тем
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        # Добавляем легенду
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#4CAF50', label='Рост напряженности'),
            Patch(facecolor='#F44336', label='Снижение напряженности'),
            Patch(facecolor='#9E9E9E', label='Стабильная ситуация')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        # Сохраняем график
        unique_id = uuid.uuid4().hex[:8]
        today_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'ai_topics_forecast_{category}_{today_str}_{unique_id}.png'
        
        static_folder = os.path.join(current_app.root_path, 'static', 'images')
        os.makedirs(static_folder, exist_ok=True)
        
        filepath = os.path.join(static_folder, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return f'/static/images/{filename}'
        
    except Exception as e:
        current_app.logger.error(f"Error generating topics chart: {str(e)}")
        plt.close()
        return create_empty_chart_simple("topics", category)