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
import math
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
from app.utils.social_tension_analyzer import get_tension_analyzer

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

def get_table_for_category(category):
    """Получение правильной таблицы для категории.
    
    Args:
        category (str): Код категории
    
    Returns:
        str: Название таблицы
    """
    if category == 'all':
        # Для всех категорий используем основную таблицу
        return "news.ukraine_universal_news"
    elif category == 'military':
        return "news.universal_military_operations"
    elif category == 'humanitarian':
        return "news.universal_humanitarian_crisis"
    elif category == 'economic':
        return "news.universal_economic_consequences"
    elif category == 'political':
        return "news.universal_political_decisions"
    elif category == 'information':
        return "news.universal_information_social"
    else:
        # Для остальных категорий используем основную таблицу
        return "news.ukraine_universal_news"

def get_table_columns(category):
    """Получение правильных столбцов для таблицы категории.
    
    Args:
        category (str): Код категории
    
    Returns:
        dict: Словарь с именами столбцов
    """
    if category in ['military', 'humanitarian', 'economic', 'political', 'information']:
        # Для специализированных таблиц (military, humanitarian, etc.)
        return {
            'source_column': 'source',
            'site_name_column': 'source',  # В специализированных таблицах нет site_name
            'url_column': 'link'  # В специализированных таблицах url называется link
        }
    else:
        # Для основной таблицы ukraine_universal_news (all и остальные категории)
        return {
            'source_column': 'source',
            'site_name_column': 'site_name',
            'url_column': 'url'
        }

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
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Запрос для получения статистики
        query = f"""
        SELECT 
            COUNT(*) as total_news,
            AVG(sentiment_score) as avg_sentiment
        FROM {table_source}
        WHERE published_date >= today() - {days}
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
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Запрос для получения данных по дням
        query = f"""
        SELECT 
            toDate(published_date) as day,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as news_count
        FROM {table_source}
        WHERE published_date >= today() - {days}
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
        
        # Используем UNION для получения данных из всех таблиц
        table_source = get_table_for_category('all')
        
        # Запрос для получения распределения по категориям
        query = f"""
        SELECT 
            category,
            count() AS news_count,
            avg(sentiment_score) AS avg_sentiment
        FROM {table_source}
        WHERE published_date >= today() - {days}
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
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Запрос для получения топ источников
        query = f"""
        SELECT 
            source,
            COUNT(*) as news_count,
            AVG(sentiment_score) as avg_sentiment
        FROM {table_source}
        WHERE published_date >= today() - {days}
        {category_condition}
        GROUP BY source
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
    """Получение списка последних новостей с анализом социальной напряженности.
    
    Query Parameters:
        category (str): Категория новостей (по умолчанию 'all')
        days (int): Количество дней для анализа (по умолчанию 7)
        limit (int): Максимальное количество новостей (по умолчанию 20)
    
    Returns:
        JSON: Список последних новостей с данными о напряженности
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 7))
        limit = int(request.args.get('limit', 20))
        
        client = get_clickhouse_client()
        tension_analyzer = get_tension_analyzer()
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        columns = get_table_columns(category)
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            if category == 'military':
                category_condition = f"AND category = 'military_operations'"
            else:
                category_condition = f"AND category = '{category}'"
        
        # Запрос для получения последних новостей
        query = f"""
        SELECT 
            published_date,
            title,
            content,
            {columns['url_column']} as url,
            {columns['source_column']} as source,
            category,
            sentiment_score
        FROM {table_source}
        WHERE published_date >= today() - {days}
        {category_condition}
        ORDER BY published_date DESC
        LIMIT {limit}
        """
        
        result = client.execute(query)
        
        news_list = []
        for row in result:
            # Анализируем социальную напряженность
            text = f"{row[1]} {row[2] or ''}"  # title + content
            tension_metrics = tension_analyzer.analyze_text_tension(text, row[1])
            
            news_list.append({
                'date': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'title': row[1],
                'url': row[3],
                'source': row[4],
                'category': row[5],
                'sentiment_score': float(row[6]),
                'tension_score': tension_metrics.tension_score,
                'tension_category': tension_metrics.category,
                'emotional_intensity': tension_metrics.emotional_intensity,
                'conflict_level': tension_metrics.conflict_level,
                'urgency_factor': tension_metrics.urgency_factor
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
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Получаем новости для пересчета
        query = f"""
        SELECT id, title, content, category
        FROM {table_source}
        WHERE 1=1 {category_condition}
        ORDER BY published_date DESC
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
                    'category': news_category,
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
            # Группируем записи по категориям для обновления соответствующих таблиц
            records_by_category = {}
            for record in updated_records:
                cat = record.get('category', 'military_operations')  # получаем категорию из результата запроса
                if cat not in records_by_category:
                    records_by_category[cat] = []
                records_by_category[cat].append(record)
            
            # Обновляем каждую таблицу отдельно
            for cat, records in records_by_category.items():
                table_name = f"news.universal_{cat}"
                for record in records:
                    update_query = f"""
                    ALTER TABLE {table_name}
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
                        current_app.logger.error(f"Error updating record {record['id']} in {table_name}: {str(e)}")
        
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
        
        # Используем UNION для получения данных из всех таблиц
        table_source = get_table_for_category('all')
        
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
        FROM {table_source}
        WHERE published_date >= today() - {days}
        GROUP BY category
        ORDER BY total_news DESC
        """
        
        result = client.execute(query)
        
        def safe_float(value):
            """Безопасное преобразование в float с защитой от NaN."""
            try:
                if value is None:
                    return 0.0
                result = float(value)
                if math.isnan(result) or math.isinf(result):
                    return 0.0
                return result
            except (ValueError, TypeError):
                return 0.0
        
        analysis_data = []
        for row in result:
            category, total, avg_sentiment, avg_pos, avg_neg, avg_neu, avg_mil, avg_hum = row
            
            analysis_data.append({
                'category': category,
                'category_name': get_category_name(category),
                'total_news': total,
                'avg_sentiment': safe_float(avg_sentiment),
                'avg_positive': safe_float(avg_pos),
                'avg_negative': safe_float(avg_neg),
                'avg_neutral': safe_float(avg_neu),
                'avg_military_intensity': safe_float(avg_mil),
                'avg_humanitarian_focus': safe_float(avg_hum)
            })
        
        return jsonify({
            'status': 'success',
            'analysis_period_days': days,
            'categories_analysis': analysis_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting sentiment analysis: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/social_tension_statistics', methods=['GET'])
def get_social_tension_statistics():
    """Получение статистики социальной напряженности.
    
    Query Parameters:
        category (str): Категория новостей (по умолчанию 'all')
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: Статистика социальной напряженности
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        tension_analyzer = get_tension_analyzer()
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Запрос для получения новостей
        query = f"""
        SELECT title, content, published_date, category, source
        FROM {table_source}
        WHERE published_date >= today() - {days}
        {category_condition}
        ORDER BY published_date DESC
        LIMIT 5000
        """
        
        results = client.execute(query)
        
        if not results:
            return jsonify({
                'status': 'success',
                'total_news': 0,
                'avg_tension': 0.0,
                'tension_distribution': {},
                'trend': 'stable'
            })
        
        def safe_float(value):
            """Безопасное преобразование в float с защитой от NaN."""
            try:
                if value is None:
                    return 0.0
                result = float(value)
                if math.isnan(result) or math.isinf(result):
                    return 0.0
                return result
            except (ValueError, TypeError):
                return 0.0
        
        # Анализ напряженности для каждой новости
        tension_scores = []
        tension_history = []
        
        for title, content, pub_date, cat, site_name in results:
            text = f"{title} {content or ''}"
            metrics = tension_analyzer.analyze_text_tension(text, title)
            safe_score = safe_float(metrics.tension_score)
            tension_scores.append(safe_score)
            tension_history.append((pub_date, safe_score))
        
        # Расчет статистики
        avg_tension = safe_float(sum(tension_scores) / len(tension_scores)) if tension_scores else 0.0
        
        # Подсчет распределения по уровням напряженности (значения уже в процентах)
        tension_distribution = {
            'low': len([s for s in tension_scores if s < 30]),
            'medium': len([s for s in tension_scores if 30 <= s < 60]),
            'high': len([s for s in tension_scores if 60 <= s < 80]),
            'critical': len([s for s in tension_scores if s >= 80])
        }
        
        # Анализ тренда
        if len(tension_history) >= 2:
            recent_scores = [score for _, score in tension_history[-10:]]
            earlier_scores = [score for _, score in tension_history[:-10]] if len(tension_history) > 10 else []
            
            if earlier_scores:
                recent_avg = sum(recent_scores) / len(recent_scores)
                earlier_avg = sum(earlier_scores) / len(earlier_scores)
                
                if recent_avg > earlier_avg + 0.1:
                    trend = 'rising'
                elif recent_avg < earlier_avg - 0.1:
                    trend = 'falling'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
        
        return jsonify({
            'status': 'success',
            'total_news': len(results),
            'avg_tension': round(safe_float(avg_tension), 2),
            'tension_distribution': tension_distribution,
            'trend': trend,
            'max_tension': round(safe_float(max(tension_scores)), 2) if tension_scores else 0.0,
            'min_tension': round(safe_float(min(tension_scores)), 2) if tension_scores else 0.0
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting social tension statistics: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/social_tension_chart', methods=['GET'])
def get_social_tension_chart():
    """Создание графика динамики социальной напряженности.
    
    Query Parameters:
        category (str): Категория новостей (по умолчанию 'all')
        days (int): Количество дней для анализа (по умолчанию 7)
        chart_type (str): Тип графика ('timeline', 'distribution', 'heatmap')
    
    Returns:
        JSON: URL созданного графика
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 7))
        chart_type = request.args.get('chart_type', 'timeline')
        
        client = get_clickhouse_client()
        tension_analyzer = get_tension_analyzer()
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Запрос для получения новостей
        query = f"""
        SELECT title, content, published_date, category, source
        FROM {table_source}
        WHERE published_date >= today() - {days}
        {category_condition}
        ORDER BY published_date DESC
        LIMIT 5000
        """
        
        results = client.execute(query)
        
        if not results:
            # Создаем пустой график с сообщением
            chart_url = create_empty_chart(chart_type, category, days)
            return jsonify({
                'status': 'success',
                'chart_url': chart_url,
                'data_points': 0,
                'message': 'Нет данных для выбранной категории'
            })
        
        # Анализ напряженности
        tension_data = []
        for title, content, pub_date, cat, site_name in results:
            text = f"{title} {content or ''}"
            metrics = tension_analyzer.analyze_text_tension(text, title)
            tension_data.append({
                'date': pub_date,
                'tension': metrics.tension_score,  # Уже в процентах (0-100)
                'category': cat,
                'source': site_name,
                'title': title
            })
        
        # Создание графика
        chart_url = create_tension_chart(tension_data, chart_type, category, days)
        
        return jsonify({
            'status': 'success',
            'chart_url': chart_url,
            'data_points': len(tension_data)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating social tension chart: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/tension_by_category', methods=['GET'])
def get_tension_by_category():
    """Получение напряженности по категориям.
    
    Query Parameters:
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: Напряженность по категориям
    """
    try:
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        tension_analyzer = get_tension_analyzer()
        
        # Используем UNION для получения данных из всех таблиц
        table_source = get_table_for_category('all')
        
        # Запрос для получения новостей по категориям
        query = f"""
        SELECT category, title, content, published_date
        FROM {table_source}
        WHERE published_date >= today() - {days}
        ORDER BY category, published_date DESC
        LIMIT 5000
        """
        
        results = client.execute(query)
        
        if not results:
            return jsonify({
                'status': 'success',
                'categories': []
            })
        
        # Группировка по категориям
        categories_data = {}
        for category, title, content, pub_date in results:
            if category not in categories_data:
                categories_data[category] = []
            
            text = f"{title} {content or ''}"
            metrics = tension_analyzer.analyze_text_tension(text, title)
            categories_data[category].append(metrics.tension_score)
        
        # Расчет статистики по категориям
        category_stats = []
        for category, tensions in categories_data.items():
            if tensions:
                # Подсчет распределения по уровням напряженности
                distribution = {
                    'low': len([s for s in tensions if s < 30]),
                    'medium': len([s for s in tensions if 30 <= s < 60]),
                    'high': len([s for s in tensions if 60 <= s < 80]),
                    'critical': len([s for s in tensions if s >= 80])
                }
                
                category_stats.append({
                    'category': category,
                    'category_name': get_category_name(category),
                    'avg_tension': round(sum(tensions) / len(tensions), 2),
                    'max_tension': round(max(tensions), 2),
                    'min_tension': round(min(tensions), 2),
                    'news_count': len(tensions),
                    'distribution': distribution
                })
        
        # Сортировка по средней напряженности
        category_stats.sort(key=lambda x: x['avg_tension'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'categories': category_stats
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting tension by category: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/tension_alerts', methods=['GET'])
def get_tension_alerts():
    """Получение предупреждений о высокой напряженности.
    
    Query Parameters:
        threshold (float): Порог напряженности для предупреждений (по умолчанию 70.0)
        hours (int): Количество часов для анализа (по умолчанию 24)
    
    Returns:
        JSON: Список предупреждений
    """
    try:
        threshold = float(request.args.get('threshold', 70.0))
        hours = int(request.args.get('hours', 24))
        
        client = get_clickhouse_client()
        tension_analyzer = get_tension_analyzer()
        
        # Используем UNION для получения данных из всех таблиц
        table_source = get_table_for_category('all')
        
        # Запрос для получения последних новостей
        query = f"""
        SELECT title, content, published_date, category, source, '' as url
        FROM {table_source}
        WHERE published_date >= now() - INTERVAL {hours} HOUR
        ORDER BY published_date DESC
        LIMIT 500
        """
        
        results = client.execute(query)
        
        alerts = []
        for title, content, pub_date, category, source, url in results:
            text = content or ""
            metrics = tension_analyzer.analyze_text_tension(text, title)
            
            if metrics.tension_score >= threshold:
                alerts.append({
                    'title': title,
                    'tension_score': round(metrics.tension_score, 2),
                    'category': metrics.category,
                    'published_date': pub_date.isoformat() if pub_date else None,
                    'source': source,
                    'url': url,
                    'news_category': category,
                    'emotional_intensity': round(metrics.emotional_intensity, 2),
                    'conflict_level': round(metrics.conflict_level, 2),
                    'urgency_factor': round(metrics.urgency_factor, 2)
                })
        
        # Сортировка по уровню напряженности
        alerts.sort(key=lambda x: x['tension_score'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'alerts_count': len(alerts),
            'threshold': threshold,
            'alerts': alerts[:50]  # Ограничиваем до 50 предупреждений
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting tension alerts: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


def create_empty_chart(chart_type, category, days):
    """Создание пустого графика с сообщением об отсутствии данных."""
    try:
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Убираем оси и добавляем текст
        ax.axis('off')
        ax.text(0.5, 0.5, f'Нет данных для категории "{category}"\nза последние {days} дней', 
                ha='center', va='center', fontsize=16, 
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))
        
        ax.set_title(f'График социальной напряженности ({chart_type})', fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Сохранение графика
        chart_filename = f"social_tension_{chart_type}_{category}_{days}d_empty_{uuid.uuid4().hex[:8]}.png"
        chart_path = os.path.join(current_app.static_folder, 'charts', chart_filename)
        
        # Создаем директорию если её нет
        os.makedirs(os.path.dirname(chart_path), exist_ok=True)
        
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return f"/static/charts/{chart_filename}"
        
    except Exception as e:
        current_app.logger.error(f"Error creating empty chart: {str(e)}")
        plt.close()
        return None


def create_tension_chart(tension_data, chart_type, category, days):
    """Создание графика социальной напряженности."""
    try:
        # Проверка на минимальное количество данных
        if not tension_data or len(tension_data) < 1:
            return create_empty_chart(chart_type, category, days)
            
        # Настройка стиля
        plt.style.use('seaborn-v0_8')
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if chart_type == 'timeline':
            # График временной динамики
            dates = [item['date'] for item in tension_data]
            tensions = [item['tension'] for item in tension_data]
            
            ax.plot(dates, tensions, linewidth=2, color='#e74c3c', alpha=0.8)
            ax.fill_between(dates, tensions, alpha=0.3, color='#e74c3c')
            
            # Добавляем горизонтальные линии для уровней напряженности
            ax.axhline(y=70, color='red', linestyle='--', alpha=0.7, label='Критический уровень')
            ax.axhline(y=50, color='orange', linestyle='--', alpha=0.7, label='Высокий уровень')
            ax.axhline(y=30, color='yellow', linestyle='--', alpha=0.7, label='Средний уровень')
            
            ax.set_title(f'Динамика социальной напряженности ({days} дней)', fontsize=16, fontweight='bold')
            ax.set_xlabel('Дата', fontsize=12)
            ax.set_ylabel('Индекс напряженности', fontsize=12)
            ax.legend()
            
        elif chart_type == 'distribution':
            # График распределения по уровням
            tensions = [item['tension'] for item in tension_data]
            
            # Создаем гистограмму
            bins = [0, 10, 30, 50, 70, 100]
            labels = ['Минимальная', 'Низкая', 'Средняя', 'Высокая', 'Критическая']
            colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c', '#8e44ad']
            
            counts, bin_edges, patches = ax.hist(tensions, bins=bins, alpha=0.7, edgecolor='black')
            
            # Применяем цвета к каждому столбцу отдельно
            for i, patch in enumerate(patches):
                if i < len(colors):
                    patch.set_facecolor(colors[i])
            
            ax.set_title(f'Распределение социальной напряженности ({days} дней)', fontsize=16, fontweight='bold')
            ax.set_xlabel('Уровень напряженности', fontsize=12)
            ax.set_ylabel('Количество новостей', fontsize=12)
            
            # Добавляем подписи к столбцам
            for i, (count, label) in enumerate(zip(counts, labels)):
                if count > 0:
                    ax.text(bins[i] + (bins[i+1] - bins[i])/2, count + 0.5, 
                           f'{int(count)}\n{label}', ha='center', va='bottom', fontsize=10)
        
        elif chart_type == 'heatmap':
            # Тепловая карта по дням и часам
            from collections import defaultdict
            import pandas as pd
            
            # Группируем данные по дням и часам
            heatmap_data = defaultdict(lambda: defaultdict(list))
            
            for item in tension_data:
                date = item['date']
                if date:
                    day = date.strftime('%Y-%m-%d')
                    hour = date.hour
                    heatmap_data[day][hour].append(item['tension'])
            
            # Создаем матрицу для тепловой карты
            days_list = sorted(heatmap_data.keys())
            hours = list(range(24))
            
            matrix = []
            for day in days_list:
                row = []
                for hour in hours:
                    if hour in heatmap_data[day] and heatmap_data[day][hour]:
                        avg_tension = sum(heatmap_data[day][hour]) / len(heatmap_data[day][hour])
                        row.append(avg_tension)
                    else:
                        row.append(0)
                matrix.append(row)
            
            if matrix:
                im = ax.imshow(matrix, cmap='Reds', aspect='auto', interpolation='nearest')
                
                ax.set_xticks(range(24))
                ax.set_xticklabels([f'{h:02d}:00' for h in range(24)], rotation=45)
                ax.set_yticks(range(len(days_list)))
                ax.set_yticklabels(days_list)
                
                ax.set_title(f'Тепловая карта напряженности по времени ({days} дней)', fontsize=16, fontweight='bold')
                ax.set_xlabel('Час дня', fontsize=12)
                ax.set_ylabel('Дата', fontsize=12)
                
                # Добавляем цветовую шкалу
                cbar = plt.colorbar(im, ax=ax)
                cbar.set_label('Индекс напряженности', fontsize=12)
        
        plt.tight_layout()
        
        # Сохранение графика
        chart_filename = f"social_tension_{chart_type}_{category}_{days}d_{uuid.uuid4().hex[:8]}.png"
        chart_path = os.path.join(current_app.static_folder, 'charts', chart_filename)
        
        # Создаем директорию если её нет
        os.makedirs(os.path.dirname(chart_path), exist_ok=True)
        
        plt.savefig(chart_path, dpi=300, bbox_inches='tight', facecolor='white')
        plt.close()
        
        return f"/static/charts/{chart_filename}"
        
    except Exception as e:
        current_app.logger.error(f"Error creating tension chart: {str(e)}")
        plt.close()
        return None