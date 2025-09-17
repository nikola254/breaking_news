# -*- coding: utf-8 -*-
"""
API для аналитики украинского конфликта.

Этот модуль содержит эндпоинты для:
- Получения статистики по украинским новостям
- Создания графиков напряженности
- Анализа распределения по категориям
- Получения списка последних новостей
"""

from flask import Blueprint, request, jsonify, current_app
import datetime
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import uuid
from clickhouse_driver import Client
from config import Config
from app.utils.ukraine_sentiment_analyzer import get_ukraine_sentiment_analyzer

# Создаем Blueprint для API украинской аналитики
ukraine_analytics_bp = Blueprint('ukraine_analytics', __name__, url_prefix='/api/ukraine_analytics')

def get_clickhouse_client():
    """Получение клиента ClickHouse."""
    return Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=Config.CLICKHOUSE_DATABASE
    )

@ukraine_analytics_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Получение общей статистики по украинским новостям.
    
    Query Parameters:
        category (str): Категория новостей (по умолчанию 'all')
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: Статистика с общим количеством новостей и средней напряженностью
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Запрос для получения статистики
        query = f"""
        SELECT 
            COUNT(*) as total_news,
            AVG(sentiment_score) as avg_sentiment
        FROM ukraine_conflict.all_news 
        WHERE parsed_date >= today() - {days}
        {category_condition}
        """
        
        result = client.execute(query)
        
        if result:
            total_news, avg_sentiment = result[0]
            return jsonify({
                'status': 'success',
                'total_news': total_news,
                'avg_sentiment': float(avg_sentiment) if avg_sentiment else 0.0
            })
        else:
            return jsonify({
                'status': 'success',
                'total_news': 0,
                'avg_sentiment': 0.0
            })
            
    except Exception as e:
        current_app.logger.error(f"Error getting statistics: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ukraine_analytics_bp.route('/tension_chart', methods=['GET'])
def get_tension_chart():
    """Создание графика динамики напряженности.
    
    Query Parameters:
        category (str): Категория новостей (по умолчанию 'all')
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: URL созданного графика
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Запрос для получения данных по дням
        query = f"""
        SELECT 
            toDate(parsed_date) as day,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as news_count
        FROM ukraine_conflict.all_news 
        WHERE parsed_date >= today() - {days}
        {category_condition}
        GROUP BY day
        ORDER BY day
        """
        
        result = client.execute(query)
        
        if not result:
            return jsonify({
                'status': 'success',
                'chart_url': None,
                'message': 'Нет данных для отображения'
            })
        
        # Создаем график
        plt.figure(figsize=(12, 6))
        sns.set_style("whitegrid")
        
        dates = [row[0] for row in result]
        sentiments = [float(row[1]) for row in result]
        counts = [row[2] for row in result]
        
        # Основной график настроений
        plt.subplot(2, 1, 1)
        plt.plot(dates, sentiments, marker='o', linewidth=3, color='#1976D2', markersize=8)
        plt.title(f'Динамика настроений в новостях\n{get_category_name(category)}', 
                  fontsize=14, fontweight='bold')
        plt.ylabel('Индекс настроений')
        plt.ylim(-1, 1)
        plt.grid(True, alpha=0.3)
        
        # График количества новостей
        plt.subplot(2, 1, 2)
        plt.bar(dates, counts, color='#4CAF50', alpha=0.7)
        plt.title('Количество новостей по дням', fontsize=12)
        plt.xlabel('Дата')
        plt.ylabel('Количество новостей')
        plt.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Сохраняем график
        chart_url = save_chart('tension', category)
        
        return jsonify({
            'status': 'success',
            'chart_url': chart_url
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating tension chart: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ukraine_analytics_bp.route('/category_chart', methods=['GET'])
def get_category_chart():
    """Создание графика распределения по категориям.
    
    Query Parameters:
        category (str): Категория новостей (игнорируется для этого графика)
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: URL созданного графика
    """
    try:
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Запрос для получения распределения по категориям
        query = f"""
        SELECT 
            category,
            COUNT(*) as news_count,
            AVG(sentiment_score) as avg_sentiment
        FROM ukraine_conflict.all_news 
        WHERE parsed_date >= today() - {days}
        GROUP BY category
        ORDER BY news_count DESC
        """
        
        result = client.execute(query)
        
        if not result:
            return jsonify({
                'status': 'success',
                'chart_url': None,
                'message': 'Нет данных для отображения'
            })
        
        # Создаем график
        plt.figure(figsize=(12, 8))
        sns.set_style("whitegrid")
        
        categories = [get_category_name(row[0]) for row in result]
        counts = [row[1] for row in result]
        sentiments = [float(row[2]) for row in result]
        
        # Цвета в зависимости от настроений
        colors = []
        for sentiment in sentiments:
            if sentiment > 0.1:
                colors.append('#4CAF50')  # Зеленый (позитивные)
            elif sentiment > -0.1:
                colors.append('#FFC107')  # Желтый (нейтральные)
            else:
                colors.append('#F44336')  # Красный (негативные)
        
        bars = plt.bar(categories, counts, color=colors, alpha=0.8, edgecolor='black', linewidth=1)
        
        # Добавляем аннотации
        for i, bar in enumerate(bars):
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + max(counts) * 0.02,
                    f'{counts[i]}\n({sentiments[i]:.2f})',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        plt.title(f'Распределение новостей по категориям (последние {days} дней)', 
                  fontsize=14, fontweight='bold')
        plt.xlabel('Категории')
        plt.ylabel('Количество новостей')
        plt.xticks(rotation=45, ha='right')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        # Сохраняем график
        chart_url = save_chart('category', 'all')
        
        return jsonify({
            'status': 'success',
            'chart_url': chart_url
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating category chart: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ukraine_analytics_bp.route('/sources_chart', methods=['GET'])
def get_sources_chart():
    """Создание графика топ источников.
    
    Query Parameters:
        category (str): Категория новостей (по умолчанию 'all')
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: URL созданного графика
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Запрос для получения топ источников
        query = f"""
        SELECT 
            site_name as source,
            COUNT(*) as news_count,
            AVG(sentiment_score) as avg_sentiment
        FROM ukraine_conflict.all_news 
        WHERE parsed_date >= today() - {days}
        {category_condition}
        GROUP BY site_name
        ORDER BY news_count DESC
        LIMIT 10
        """
        
        result = client.execute(query)
        
        if not result:
            return jsonify({
                'status': 'success',
                'chart_url': None,
                'message': 'Нет данных для отображения'
            })
        
        # Создаем график
        plt.figure(figsize=(12, 8))
        sns.set_style("whitegrid")
        
        sources = [row[0] for row in result]
        counts = [row[1] for row in result]
        sentiments = [float(row[2]) for row in result]
        
        # Горизонтальный барный график
        bars = plt.barh(sources, counts, color='#2196F3', alpha=0.8, edgecolor='black', linewidth=1)
        
        # Добавляем аннотации
        for i, bar in enumerate(bars):
            width = bar.get_width()
            plt.text(width + max(counts) * 0.02, bar.get_y() + bar.get_height()/2.,
                    f'{counts[i]} (тон: {sentiments[i]:.2f})',
                    ha='left', va='center', fontsize=10, fontweight='bold')
        
        plt.title(f'Топ-10 источников новостей\n{get_category_name(category)} (последние {days} дней)', 
                  fontsize=14, fontweight='bold')
        plt.xlabel('Количество новостей')
        plt.ylabel('Источники')
        plt.grid(True, alpha=0.3, axis='x')
        plt.tight_layout()
        
        # Сохраняем график
        chart_url = save_chart('sources', category)
        
        return jsonify({
            'status': 'success',
            'chart_url': chart_url
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating sources chart: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ukraine_analytics_bp.route('/recent_news', methods=['GET'])
def get_recent_news():
    """Получение списка последних новостей.
    
    Query Parameters:
        category (str): Категория новостей (по умолчанию 'all')
        days (int): Количество дней для анализа (по умолчанию 7)
        limit (int): Максимальное количество новостей (по умолчанию 20)
    
    Returns:
        JSON: Список последних новостей
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 20))
        
        client = get_clickhouse_client()
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Запрос для получения последних новостей
        query = f"""
        SELECT 
            parsed_date,
            title,
            url,
            site_name,
            category,
            sentiment_score
        FROM ukraine_conflict.all_news 
        WHERE parsed_date >= today() - {days}
        {category_condition}
        ORDER BY parsed_date DESC
        LIMIT {limit}
        """
        
        result = client.execute(query)
        
        news_list = []
        for row in result:
            news_list.append({
                'date': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'title': row[1],
                'url': row[2],
                'source': row[3],
                'category': row[4],
                'sentiment_score': float(row[5])
            })
        
        return jsonify({
            'status': 'success',
            'news': news_list
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting recent news: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

def save_chart(chart_type, category):
    """Сохранение графика и возврат URL.
    
    Args:
        chart_type (str): Тип графика
        category (str): Категория
    
    Returns:
        str: URL сохраненного графика
    """
    unique_id = uuid.uuid4().hex[:8]
    today_str = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'ukraine_{chart_type}_{category}_{today_str}_{unique_id}.png'
    
    static_folder = os.path.join(current_app.root_path, 'static', 'images')
    os.makedirs(static_folder, exist_ok=True)
    
    filepath = os.path.join(static_folder, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    
    return f'/static/images/{filename}'

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
        'other': 'Прочее'
    }
    return categories.get(category, category.title())

@ukraine_analytics_bp.route('/recalculate_sentiment', methods=['POST'])
def recalculate_sentiment():
    """Пересчет тональности для существующих новостей с использованием нового анализатора.
    
    Query Parameters:
        limit (int): Количество новостей для обработки (по умолчанию 100)
        category (str): Категория новостей для обработки (по умолчанию 'all')
    
    Returns:
        JSON: Результат пересчета тональности
    """
    try:
        limit = int(request.args.get('limit', 100))
        category = request.args.get('category', 'all')
        
        client = get_clickhouse_client()
        analyzer = get_ukraine_sentiment_analyzer()
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Получаем новости для пересчета
        query = f"""
        SELECT id, title, content, category
        FROM ukraine_conflict.all_news 
        WHERE 1=1 {category_condition}
        ORDER BY parsed_date DESC
        LIMIT {limit}
        """
        
        result = client.execute(query)
        
        if not result:
            return jsonify({
                'status': 'success',
                'message': 'Нет новостей для обработки',
                'processed_count': 0
            })
        
        processed_count = 0
        updated_records = []
        
        for row in result:
            news_id, title, content, news_category = row
            
            # Объединяем заголовок и содержание для анализа
            text_for_analysis = f"{title or ''} {content or ''}"
            
            if text_for_analysis.strip():
                # Анализируем тональность
                sentiment_result = analyzer.analyze_sentiment(text_for_analysis)
                
                # Подготавливаем данные для обновления
                updated_records.append({
                    'id': news_id,
                    'sentiment_score': sentiment_result['sentiment_score'],
                    'positive_score': sentiment_result['positive_score'],
                    'negative_score': sentiment_result['negative_score'],
                    'neutral_score': sentiment_result['neutral_score'],
                    'military_intensity': sentiment_result['military_intensity'],
                    'humanitarian_focus': sentiment_result['humanitarian_focus']
                })
                
                processed_count += 1
        
        # Обновляем записи в базе данных
        if updated_records:
            for record in updated_records:
                update_query = f"""
                ALTER TABLE ukraine_conflict.all_news 
                UPDATE 
                    sentiment_score = {record['sentiment_score']},
                    positive_score = {record['positive_score']},
                    negative_score = {record['negative_score']},
                    neutral_score = {record['neutral_score']},
                    military_intensity = {record['military_intensity']},
                    humanitarian_focus = {record['humanitarian_focus']}
                WHERE id = '{record['id']}'
                """
                
                try:
                    client.execute(update_query)
                except Exception as e:
                    current_app.logger.error(f"Error updating record {record['id']}: {str(e)}")
        
        return jsonify({
            'status': 'success',
            'message': f'Успешно обработано {processed_count} новостей',
            'processed_count': processed_count,
            'category': category
        })
        
    except Exception as e:
        current_app.logger.error(f"Error recalculating sentiment: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ukraine_analytics_bp.route('/sentiment_analysis', methods=['GET'])
def get_sentiment_analysis():
    """Получение детального анализа тональности по категориям.
    
    Query Parameters:
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: Детальный анализ тональности
    """
    try:
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Запрос для получения детальной статистики тональности
        query = f"""
        SELECT 
            category,
            COUNT(*) as total_news,
            AVG(sentiment_score) as avg_sentiment,
            AVG(positive_score) as avg_positive,
            AVG(negative_score) as avg_negative,
            AVG(neutral_score) as avg_neutral,
            AVG(military_intensity) as avg_military_intensity,
            AVG(humanitarian_focus) as avg_humanitarian_focus
        FROM ukraine_conflict.all_news 
        WHERE parsed_date >= today() - {days}
        GROUP BY category
        ORDER BY total_news DESC
        """
        
        result = client.execute(query)
        
        analysis_data = []
        for row in result:
            category, total, avg_sentiment, avg_pos, avg_neg, avg_neu, avg_mil, avg_hum = row
            
            analysis_data.append({
                'category': category,
                'category_name': get_category_name(category),
                'total_news': total,
                'avg_sentiment': float(avg_sentiment) if avg_sentiment else 0.0,
                'avg_positive': float(avg_pos) if avg_pos else 0.0,
                'avg_negative': float(avg_neg) if avg_neg else 0.0,
                'avg_neutral': float(avg_neu) if avg_neu else 0.0,
                'avg_military_intensity': float(avg_mil) if avg_mil else 0.0,
                'avg_humanitarian_focus': float(avg_hum) if avg_hum else 0.0
            })
        
        return jsonify({
            'status': 'success',
            'analysis_period_days': days,
            'categories_analysis': analysis_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting sentiment analysis: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500