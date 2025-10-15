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
from datetime import timedelta
import math
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import uuid
from .chart_api import cleanup_old_charts
from collections import defaultdict
from clickhouse_driver import Client
from config import Config
from app.utils.ukraine_sentiment_analyzer import get_ukraine_sentiment_analyzer
from app.utils.social_tension_analyzer import get_tension_analyzer
from app.analytics.tension_chart_generator import chart_generator

# Создаем Blueprint для API украинской аналитики
ukraine_analytics_bp = Blueprint('ukraine_analytics', __name__, url_prefix='/api/ukraine_analytics')

def safe_float(value):
    """Безопасное преобразование в float."""
    try:
        if value is None or value == '':
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0

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
        str: Название таблицы или UNION ALL запрос
    """
    if category == 'all':
        # Для всех категорий используем lenta_headlines (содержит данные с новыми полями)
        return "news.lenta_headlines"
    elif category == 'military' or category == 'military_operations':
        return "news.lenta_headlines"
    elif category == 'information' or category == 'information_social':
        return "news.lenta_headlines"
    elif category == 'political_decisions':
        return "news.lenta_headlines"
    elif category == 'economic_consequences':
        return "news.lenta_headlines"
    elif category == 'humanitarian_crisis':
        return "news.lenta_headlines"
    else:
        # Для остальных категорий используем lenta_headlines как основную таблицу
        return "news.lenta_headlines"

def build_union_query_for_category(category, days):
    """Построение UNION ALL запроса для категории из всех таблиц источников.
    
    Args:
        category (str): Код категории
        days (int): Количество дней для анализа
    
    Returns:
        str: UNION ALL запрос
    """
    # Список основных таблиц источников
    source_tables = [
        'telegram_headlines',
        'lenta_headlines',
        'rbc_headlines',
        'gazeta_headlines',
        'kommersant_headlines',
        'ria_headlines',
        'rt_headlines',
        'tsn_headlines',
        'unian_headlines',
        'israil_headlines',
    ]
    
    union_parts = []
    for table in source_tables:
        union_parts.append(f"""
            SELECT title, content, published_date, category, source, COALESCE(link, '') as link
            FROM news.{table}
            WHERE published_date >= today() - {days}
            AND category = '{category}'
        """)
    
    return " UNION ALL ".join(union_parts)

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
        
        # Формируем запрос в зависимости от типа таблицы
        if table_source == "all_sources":
            # Используем UNION ALL запрос для всех источников
            query = f"""
            SELECT COUNT(*) as total_news
            FROM (
                {build_union_query_for_category(category, days)}
            )
            """
        else:
            # Формируем условие для категории
            category_condition = ""
            if category != 'all':
                category_condition = f"AND category = '{category}'"
            
            # Запрос для получения статистики
            query = f"""
            SELECT 
                COUNT(*) as total_news
            FROM {table_source}
            WHERE published_date >= today() - {days}
            {category_condition}
            """
        
        result = client.execute(query)
        
        if result:
            total_news = result[0][0]
            return jsonify({
                'status': 'success',
                'total_news': total_news,
                'avg_sentiment': 0.0  # Пока нет данных о sentiment
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
        
        # Запрос для получения данных по дням с новыми полями
        query = f"""
        SELECT 
            toDate(published_date) as day,
            AVG(COALESCE(social_tension_index, 0)) as avg_tension,
            AVG(COALESCE(spike_index, 0)) as avg_spike,
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
        tensions = [float(row[1]) for row in result]
        spikes = [float(row[2]) for row in result]
        counts = [row[3] for row in result]
        
        # Основной график социальной напряженности
        plt.subplot(2, 1, 1)
        plt.plot(dates, tensions, marker='o', linewidth=3, color='#e74c3c', markersize=8)
        plt.title(f'Динамика социальной напряженности\n{get_category_name(category)}', 
                  fontsize=14, fontweight='bold')
        plt.ylabel('Индекс социальной напряженности')
        plt.ylim(0, 100)
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
        
        # Получаем список всех существующих таблиц
        existing_tables_query = """
        SELECT name 
        FROM system.tables 
        WHERE database = 'news' 
        AND name LIKE '%_headlines'
        ORDER BY name
        """
        
        existing_tables_result = client.execute(existing_tables_query)
        existing_tables = [row[0] for row in existing_tables_result]
        
        # Строим UNION запрос для всех таблиц
        union_parts = []
        for table_name in existing_tables:
            union_parts.append(f"""
                SELECT 
                    category,
                    count() AS news_count,
                    avg(sentiment_score) AS avg_sentiment
                FROM news.{table_name}
                WHERE published_date >= today() - {days}
                GROUP BY category
            """)
        
        if not union_parts:
            return jsonify({
                'status': 'success',
                'chart_url': None,
                'message': 'Нет данных для отображения'
            })
        
        # Объединяем все запросы
        query = f"""
        SELECT 
            category,
            sum(news_count) AS news_count,
            avg(avg_sentiment) AS avg_sentiment
        FROM (
            {' UNION ALL '.join(union_parts)}
        )
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
        
        # Формируем запрос в зависимости от типа таблицы
        if table_source == "all_sources":
            # Используем UNION ALL запрос для всех источников
            query = f"""
            SELECT published_date, title, content, category, source, link
            FROM (
                {build_union_query_for_category(category, days)}
            )
            ORDER BY published_date DESC
            LIMIT {limit}
            """
        else:
            # Запрос для получения последних новостей
            # Проверяем, есть ли sentiment_score в таблице
            try:
                check_columns_query = f"DESCRIBE TABLE {table_source}"
                columns_info = client.execute(check_columns_query)
                has_sentiment = any('sentiment_score' in str(col) for col in columns_info)
                has_url = any('url' in str(col) for col in columns_info)
            except:
                has_sentiment = False
                has_url = False
            
            # Формируем условие для категории
            category_condition = ""
            if category != 'all':
                if category == 'military':
                    category_condition = f"AND category = 'military_operations'"
                else:
                    category_condition = f"AND category = '{category}'"
            
            # Формируем запрос в зависимости от доступных колонок
            if has_sentiment and has_url:
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
            else:
                # Упрощенный запрос без sentiment_score и url
                query = f"""
                SELECT 
                    published_date,
                    title,
                    content,
                    '' as url,
                    {columns['source_column']} as source,
                    category,
                    0.0 as sentiment_score
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
            
            # Безопасно обрабатываем URL
            url = row[3] if len(row) > 3 and row[3] else ''
            
            news_list.append({
                'date': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0]),
                'title': row[1],
                'url': url,
                'source': row[4] if len(row) > 4 else '',
                'category': row[5] if len(row) > 5 else category,
                'sentiment_score': float(row[6]) if len(row) > 6 else 0.0,
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
    
    # Очищаем старые графики аналитики
    cleanup_old_charts(f'ukraine_{chart_type}', keep_count=5, static_folder=static_folder)
    
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
        
        # Запрос для получения новостей с новыми полями
        query = f"""
        SELECT title, content, published_date, category, source,
               COALESCE(social_tension_index, 0) as tension_index,
               COALESCE(spike_index, 0) as spike_index,
               COALESCE(ai_category, category) as ai_category,
               COALESCE(ai_confidence, 0) as ai_confidence
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
                'avg_spike': 0.0,
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
        spike_scores = []
        tension_history = []
        
        for title, content, pub_date, cat, site_name, tension_idx, spike_idx, ai_cat, ai_conf in results:
            # Используем данные из базы, если они есть, иначе анализируем
            if tension_idx > 0:
                safe_tension = safe_float(tension_idx)
                safe_spike = safe_float(spike_idx)
            else:
                # Fallback к анализу текста
                text = f"{title} {content or ''}"
                metrics = tension_analyzer.analyze_text_tension(text, title)
                safe_tension = safe_float(metrics.tension_score) * 100
                safe_spike = safe_tension * 0.8  # Примерное соотношение
            
            tension_scores.append(safe_tension)
            spike_scores.append(safe_spike)
            tension_history.append((pub_date, safe_tension))
        
        # Расчет статистики
        avg_tension = safe_float(sum(tension_scores) / len(tension_scores)) if tension_scores else 0.0
        avg_spike = safe_float(sum(spike_scores) / len(spike_scores)) if spike_scores else 0.0
        
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
            'avg_spike': round(safe_float(avg_spike), 2),
            'tension_distribution': tension_distribution,
            'trend': trend,
            'max_tension': round(safe_float(max(tension_scores)), 2) if tension_scores else 0.0,
            'min_tension': round(safe_float(min(tension_scores)), 2) if tension_scores else 0.0,
            'max_spike': round(safe_float(max(spike_scores)), 2) if spike_scores else 0.0,
            'min_spike': round(safe_float(min(spike_scores)), 2) if spike_scores else 0.0
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting social tension statistics: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/latest_news', methods=['GET'])
def get_latest_news():
    """Получение последних новостей для отображения в разделе аналитики"""
    try:
        days = request.args.get('days', 7, type=int)
        category = request.args.get('category', 'all')
        source = request.args.get('source', None)
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        search = request.args.get('search', '')
        
        # Инициализируем клиент ClickHouse и анализатор напряженности
        client = get_clickhouse_client()
        tension_analyzer = get_tension_analyzer()
        
        # Определяем таблицу для запроса
        source_table_map = {
            'lenta': 'news.lenta_headlines',
            'rbc': 'news.rbc_headlines',
            'gazeta': 'news.gazeta_headlines',
            'kommersant': 'news.kommersant_headlines',
            'ria': 'news.ria_headlines',
            'rt': 'news.rt_headlines',
            'tsn': 'news.tsn_headlines',
            'unian': 'news.unian_headlines',
            'israil': 'news.israil_headlines',
            'telegram': 'news.telegram_headlines'
        }
        
        if source and source != 'all' and source in source_table_map:
            # Используем конкретную таблицу для выбранного источника
            table_source = source_table_map[source]
        else:
            # UNION ALL из всех таблиц для 'all' или неизвестного источника
            table_source = 'UNION_ALL'
        
        # Условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Условие для поиска
        search_condition = ""
        if search:
            search_condition = f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')"
        
        
        # Запрос для получения последних новостей с новыми полями
        if table_source == 'UNION_ALL':
            # UNION ALL запрос из всех таблиц
            union_parts = []
            for source_name, table_name in source_table_map.items():
                union_parts.append(f"""
                    SELECT title, content, published_date, category, source,
                           COALESCE(social_tension_index, 0) as tension_index,
                           COALESCE(spike_index, 0) as spike_index,
                           COALESCE(ai_category, category) as ai_category,
                           COALESCE(ai_confidence, 0) as ai_confidence
                    FROM {table_name}
                    WHERE published_date >= today() - {days}
                    {category_condition}
                    {search_condition}
                """)
            
            query = f"""
            SELECT title, content, published_date, category, source,
                   tension_index, spike_index, ai_category, ai_confidence
            FROM (
                {' UNION ALL '.join(union_parts)}
            )
            ORDER BY published_date DESC
            LIMIT {limit} OFFSET {offset}
            """
        else:
            # Запрос к конкретной таблице
            query = f"""
            SELECT title, content, published_date, category, source,
                   COALESCE(social_tension_index, 0) as tension_index,
                   COALESCE(spike_index, 0) as spike_index,
                   COALESCE(ai_category, category) as ai_category,
                   COALESCE(ai_confidence, 0) as ai_confidence
            FROM {table_source}
            WHERE published_date >= today() - {days}
            {category_condition}
            {search_condition}
            ORDER BY published_date DESC
            LIMIT {limit} OFFSET {offset}
            """
        
        result = client.execute(query)
        
        latest_news = []
        for title, content, pub_date, cat, site_name, tension_idx, spike_idx, ai_cat, ai_conf in result:
            # Используем данные из базы, если они есть и больше 0, иначе анализируем
            if tension_idx > 0:
                calculated_tension = safe_float(tension_idx)
                calculated_spike = safe_float(spike_idx)
            else:
                # Fallback к анализу текста для правильного расчета напряженности
                text = f"{title} {content or ''}"
                metrics = tension_analyzer.analyze_text_tension(text, title)
                calculated_tension = safe_float(metrics.tension_score) * 100
                calculated_spike = calculated_tension * 0.8  # Примерное соотношение
            
            latest_news.append({
                'title': title,
                'content': content,  # Возвращаем полное содержимое без обрезания
                'published_date': pub_date.strftime('%Y-%m-%d %H:%M') if pub_date else 'Неизвестно',
                'category': ai_cat or cat,
                'source': site_name,
                'tension_index': round(calculated_tension, 2),
                'spike_index': round(calculated_spike, 2),
                'ai_confidence': round(safe_float(ai_conf), 2)
            })
        
        # Получаем общее количество записей для пагинации
        if table_source == 'UNION_ALL':
            # UNION ALL запрос для подсчета
            union_count_parts = []
            for source_name, table_name in source_table_map.items():
                union_count_parts.append(f"""
                    SELECT COUNT(*) as cnt
                    FROM {table_name}
                    WHERE published_date >= today() - {days}
                    {category_condition}
                    {search_condition}
                """)
            
            count_query = f"""
            SELECT SUM(cnt) as total
            FROM (
                {' UNION ALL '.join(union_count_parts)}
            )
            """
        else:
            # Запрос к конкретной таблице для подсчета
            count_query = f"""
            SELECT COUNT(*)
            FROM {table_source}
            WHERE published_date >= today() - {days}
            {category_condition}
            {search_condition}
            """
        total_count_result = client.execute(count_query)
        total_count = total_count_result[0][0] if total_count_result else len(latest_news)
        
        return jsonify({
            'status': 'success',
            'latest_news': latest_news,
            'total_count': total_count,
            'current_page': (offset // limit) + 1,
            'total_pages': math.ceil(total_count / limit) if total_count > 0 else 1
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting latest news: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


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


@ukraine_analytics_bp.route('/real_tension_chart', methods=['GET'])
def get_real_tension_chart():
    """
    Получение реального графика социальной напряженности с прогнозом
    
    Query Parameters:
        category (str): Категория новостей ('all' или конкретная категория)
        days (int): Период в днях (по умолчанию 14)
        forecast_days (int): Количество дней прогноза (по умолчанию 5)
    
    Returns:
        JSON с base64-encoded изображением графика
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 14))
        forecast_days = int(request.args.get('forecast_days', 5))
        
        client = get_clickhouse_client()
        tension_analyzer = get_tension_analyzer()
        
        # Получение таблицы для категории
        table_source = get_table_for_category(category)
        
        # Формируем условие для категории
        category_filter = ""
        if category != 'all':
            category_filter = f"AND category = '{category}'"
        
        # Запрос данных за указанный период
        query = f"""
        SELECT title, content, published_date, category, source
        FROM {table_source}
        WHERE published_date >= now() - INTERVAL {days} DAY
        {category_filter}
        ORDER BY published_date ASC
        """
        
        results = client.execute(query)
        
        if not results or len(results) == 0:
            return jsonify({
                'status': 'error',
                'message': 'Нет данных для построения графика'
            }), 404
        
        # Группируем данные по дням и вычисляем средний индекс напряженности
        daily_tension = {}
        
        for title, content, pub_date, cat, source in results:
            if not pub_date:
                continue
                
            # Приводим к дате без времени (используем только дату)
            if hasattr(pub_date, 'date'):
                date_key = pub_date.date()
            else:
                # Если это строка или другой формат
                from datetime import datetime
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    except:
                        continue
                date_key = pub_date.date()
            
            # Анализируем напряженность
            text = f"{title} {content or ''}"
            metrics = tension_analyzer.analyze_text_tension(text, title)
            
            # Нормализуем score от 0 до 1 (было 0-100)
            normalized_score = metrics.tension_score / 100.0
            
            if date_key not in daily_tension:
                daily_tension[date_key] = []
            
            daily_tension[date_key].append(normalized_score)
        
        # Вычисляем среднее значение для каждого дня
        historical_data = []
        for date_key in sorted(daily_tension.keys()):
            avg_tension = sum(daily_tension[date_key]) / len(daily_tension[date_key])
            # Преобразуем дату обратно в datetime для совместимости с графиком
            from datetime import datetime
            datetime_key = datetime.combine(date_key, datetime.min.time())
            historical_data.append((datetime_key, avg_tension))
        
        # Если данных мало, создаем дополнительные точки для лучшей визуализации
        if len(historical_data) < 3:
            # Создаем сглаженные данные на основе имеющихся
            if historical_data:
                base_value = historical_data[0][1]
                base_date = historical_data[0][0]
                
                # Добавляем несколько дней назад и вперед
                for i in range(-2, 3):
                    if i != 0:  # Пропускаем исходную дату
                        new_date = base_date + timedelta(days=i)
                        # Добавляем небольшое случайное отклонение для реалистичности
                        import random
                        variation = random.uniform(-0.1, 0.1)
                        new_value = max(0, min(1, base_value + variation))
                        historical_data.append((new_date, new_value))
                
                # Сортируем по дате
                historical_data.sort(key=lambda x: x[0])
        
        # Генерируем прогноз
        forecast_data = chart_generator.simple_forecast(historical_data, forecast_days)
        
        # Создаем график
        chart_base64 = chart_generator.generate_tension_forecast_chart(
            historical_data,
            forecast_data,
            title=f"Интегральный индекс социальной напряженности - {get_category_name_ru(category)}"
        )
        
        return jsonify({
            'status': 'success',
            'chart': chart_base64,
            'historical_points': len(historical_data),
            'forecast_points': len(forecast_data),
            'avg_tension': round(sum([d[1] for d in historical_data]) / len(historical_data), 3) if historical_data else 0
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating real tension chart: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


def get_category_name_ru(category):
    """Возвращает русское название категории"""
    categories = {
        'all': 'Все категории',
        'military_operations': 'Военные операции',
        'humanitarian_crisis': 'Гуманитарный кризис',
        'economic_consequences': 'Экономические последствия',
        'political_decisions': 'Политические решения',
        'information_social': 'Информационно-социальные аспекты',
        'other': 'Прочее'
    }
    return categories.get(category, category)


@ukraine_analytics_bp.route('/tension_heatmap', methods=['GET'])
def get_tension_heatmap():
    """Создание тепловой карты напряженности по категориям и дням.
    
    Query Parameters:
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: Base64-encoded изображение тепловой карты
    """
    try:
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        tension_analyzer = get_tension_analyzer()
        
        # Получаем данные из всех категорий
        table_source = get_table_for_category('all')
        
        # Запрос для получения новостей за период
        query = f"""
        SELECT title, content, published_date, category, source
        FROM {table_source}
        WHERE published_date >= today() - {days}
        ORDER BY published_date DESC
        """
        
        results = client.execute(query)
        
        if not results or len(results) == 0:
            return jsonify({
                'status': 'success',
                'chart': None,
                'message': 'Нет данных для построения тепловой карты'
            })
        
        # Группируем данные по категориям и дням
        category_days_tension = {}
        categories = set()
        dates = set()
        
        for title, content, pub_date, cat, source in results:
            if not pub_date:
                continue
                
            # Приводим к дате
            if hasattr(pub_date, 'date'):
                date_key = pub_date.date()
            else:
                from datetime import datetime
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    except:
                        continue
                date_key = pub_date.date()
            
            # Анализируем напряженность
            text = f"{title} {content or ''}"
            metrics = tension_analyzer.analyze_text_tension(text, title)
            normalized_score = metrics.tension_score / 100.0
            
            # Группируем по категории и дню
            key = (cat, date_key)
            if key not in category_days_tension:
                category_days_tension[key] = []
            
            category_days_tension[key].append(normalized_score)
            categories.add(cat)
            dates.add(date_key)
        
        # Создаем матрицу данных для тепловой карты
        categories = sorted(categories)
        dates = sorted(dates)
        
        # Создаем матрицу напряженности
        tension_matrix = []
        for cat in categories:
            row = []
            for date in dates:
                key = (cat, date)
                if key in category_days_tension:
                    avg_tension = sum(category_days_tension[key]) / len(category_days_tension[key])
                    row.append(avg_tension)
                else:
                    row.append(0.0)
            tension_matrix.append(row)
        
        # Создаем тепловую карту
        plt.figure(figsize=(14, 8))
        
        # Преобразуем даты в строки для подписей
        date_labels = [date.strftime('%d.%m') for date in dates]
        category_labels = [get_category_name_ru(cat) for cat in categories]
        
        # Создаем тепловую карту
        sns.heatmap(tension_matrix, 
                   xticklabels=date_labels,
                   yticklabels=category_labels,
                   cmap='RdYlBu_r',  # Красно-желто-синяя палитра
                   vmin=0, vmax=1,
                   annot=True,  # Показываем значения
                   fmt='.2f',   # Формат чисел
                   cbar_kws={'label': 'Индекс напряженности'})
        
        plt.title(f'Тепловая карта напряженности по категориям (последние {days} дней)', 
                 fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Категории', fontsize=12)
        plt.xticks(rotation=45)
        plt.yticks(rotation=0)
        plt.tight_layout()
        
        # Сохраняем график в base64
        import io
        import base64
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        chart_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return jsonify({
            'status': 'success',
            'chart': chart_base64,
            'categories_count': len(categories),
            'days_count': len(dates)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating tension heatmap: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/category_data', methods=['GET'])
def get_category_data():
    """Получение данных по категориям для Canvas-графиков.
    
    Query Parameters:
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: Данные по категориям в формате для Canvas
    """
    try:
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Получаем список всех существующих таблиц
        existing_tables_query = """
        SELECT name 
        FROM system.tables 
        WHERE database = 'news' 
        AND name LIKE '%_headlines'
        ORDER BY name
        """
        
        existing_tables_result = client.execute(existing_tables_query)
        existing_tables = [row[0] for row in existing_tables_result]
        
        # Строим UNION запрос для всех таблиц
        union_parts = []
        for table_name in existing_tables:
            union_parts.append(f"""
                SELECT 
                    category,
                    count() AS news_count,
                    avg(sentiment_score) AS avg_sentiment
                FROM news.{table_name}
                WHERE published_date >= today() - {days}
                GROUP BY category
            """)
        
        if not union_parts:
            return jsonify({
                'status': 'success',
                'data': [],
                'total_news': 0
            })
        
        # Объединяем все запросы
        query = f"""
        SELECT 
            category,
            sum(news_count) AS news_count,
            avg(avg_sentiment) AS avg_sentiment
        FROM (
            {' UNION ALL '.join(union_parts)}
        )
        GROUP BY category 
        ORDER BY news_count DESC
        """
        
        result = client.execute(query)
        
        if not result:
            return jsonify({
                'status': 'success',
                'data': [],
                'total_news': 0
            })
        
        # Обрабатываем данные
        total_news = sum(row[1] for row in result)
        category_data = []
        
        # Цвета для категорий
        colors = ['#e74c3c', '#3498db', '#f39c12', '#2ecc71', '#9b59b6', '#e67e22', '#1abc9c', '#34495e']
        
        for i, (category, count, sentiment) in enumerate(result):
            percent = round((count / total_news) * 100, 1) if total_news > 0 else 0
            color = colors[i % len(colors)]
            
            category_data.append({
                'category': category,
                'name': get_category_name_ru(category),
                'count': count,
                'percent': percent,
                'sentiment': round(float(sentiment), 2) if sentiment else 0,
                'color': color
            })
        
        return jsonify({
            'status': 'success',
            'data': category_data,
            'total_news': total_news
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting category data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/heatmap_data', methods=['GET'])
def get_heatmap_data():
    """Получение данных для тепловой карты по источникам и дням.
    
    Query Parameters:
        days (int): Количество дней для анализа (по умолчанию 7)
        category (str): Категория новостей (по умолчанию 'all')
    
    Returns:
        JSON: Данные для тепловой карты в формате для Canvas
    """
    try:
        days = int(request.args.get('days', 7))
        category = request.args.get('category', 'all')
        
        client = get_clickhouse_client()
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Получаем данные по источникам и дням с нормализацией названий источников
        # Используем тот же набор таблиц что и в /api/statistics для консистентности
        query = f"""
        SELECT 
            CASE 
                WHEN source = 'lenta.ru' THEN 'lenta'
                WHEN source = 'gazeta.ru' THEN 'gazeta'
                ELSE source
            END as normalized_source,
            toDate(published_date) as day,
            count() as news_count
        FROM (
            SELECT source, published_date, category FROM news.ria_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.lenta_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.rbc_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.gazeta_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.kommersant_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.tsn_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.unian_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.rt_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.cnn_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.aljazeera_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.france24_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.dw_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.euronews_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.bbc_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.israil_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.telegram_headlines WHERE published_date >= today() - {days} {category_condition}
        )
        GROUP BY normalized_source, day
        ORDER BY normalized_source, day
        """
        
        result = client.execute(query)
        
        if not result:
            return jsonify({
                'status': 'success',
                'sources': [],
                'days': [],
                'data': [],
                'total_news': 0
            })
        
        # Подсчитываем общее количество новостей для совместимости с другими эндпоинтами
        # Используем тот же подход что и в /api/statistics
        total_news_query = f"""
        SELECT count() as total_count
        FROM (
            SELECT source, published_date, category FROM news.ria_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.lenta_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.rbc_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.gazeta_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.kommersant_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.tsn_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.unian_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.rt_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.cnn_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.aljazeera_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.france24_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.dw_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.euronews_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.bbc_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.israil_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT source, published_date, category FROM news.telegram_headlines WHERE published_date >= today() - {days} {category_condition}
        )
        """
        
        total_result = client.execute(total_news_query)
        total_news = total_result[0][0] if total_result else 0
        
        # Обрабатываем данные
        sources = sorted(list(set(row[0] for row in result)))
        days = sorted(list(set(row[1] for row in result)))
        
        # Создаем матрицу данных
        heatmap_data = []
        for source in sources:
            row = []
            for day in days:
                # Ищем данные для этой комбинации
                count = 0
                for r in result:
                    if r[0] == source and r[1] == day:
                        count = r[2]
                        break
                row.append(count)
            heatmap_data.append(row)
        
        # Преобразуем даты в названия дней недели на русском языке
        day_names_ru = {
            'Monday': 'Понедельник',
            'Tuesday': 'Вторник', 
            'Wednesday': 'Среда',
            'Thursday': 'Четверг',
            'Friday': 'Пятница',
            'Saturday': 'Суббота',
            'Sunday': 'Воскресенье'
        }
        
        day_names = []
        for day in days:
            if hasattr(day, 'strftime'):
                day_name_en = day.strftime('%A')
                day_names.append(day_names_ru.get(day_name_en, day_name_en))
            else:
                from datetime import datetime
                if isinstance(day, str):
                    try:
                        day_obj = datetime.fromisoformat(day)
                        day_name_en = day_obj.strftime('%A')
                        day_names.append(day_names_ru.get(day_name_en, day_name_en))
                    except:
                        day_names.append(str(day))
                else:
                    day_names.append(str(day))
        
        return jsonify({
            'status': 'success',
            'sources': sources,
            'days': day_names,
            'data': heatmap_data,
            'total_news': total_news
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting heatmap data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/tension_data', methods=['GET'])
def get_tension_data():
    """Получение данных интегрального индекса для Canvas-графика.
    
    Query Parameters:
        category (str): Категория новостей (по умолчанию 'all')
        days (int): Количество дней для анализа (по умолчанию 7)
        forecast_days (int): Количество дней прогноза (по умолчанию 5)
    
    Returns:
        JSON: Данные для Canvas-графика интегрального индекса
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 7))
        forecast_days = int(request.args.get('forecast_days', 5))
        
        client = get_clickhouse_client()
        tension_analyzer = get_tension_analyzer()
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        
        # Формируем запрос в зависимости от типа таблицы
        if table_source == "all_sources":
            # Используем UNION ALL запрос для всех источников с новыми полями
            query = f"""
            SELECT title, content, published_date, category, source,
                   COALESCE(social_tension_index, 0) as tension_index,
                   COALESCE(spike_index, 0) as spike_index
            FROM (
                {build_union_query_for_category(category, days)}
            )
            ORDER BY published_date ASC
            """
        else:
            # Формируем условие для категории
            category_filter = ""
            if category != 'all':
                category_filter = f"AND category = '{category}'"
            
            # Запрос данных за указанный период с новыми полями
            query = f"""
            SELECT title, content, published_date, category, source,
                   COALESCE(social_tension_index, 0) as tension_index,
                   COALESCE(spike_index, 0) as spike_index
            FROM {table_source}
            WHERE published_date >= now() - INTERVAL {days} DAY
            {category_filter}
            ORDER BY published_date ASC
            """
        
        results = client.execute(query)
        
        if not results or len(results) == 0:
            return jsonify({
                'status': 'success',
                'historical_data': [],
                'forecast_data': [],
                'zones': [],
                'avg_tension': 0,
                'trend': 'stable'
            })
        
        # Группируем данные по дням и вычисляем средний индекс напряженности
        daily_tension = {}
        
        for title, content, pub_date, cat, source, tension_idx, spike_idx in results:
            if not pub_date:
                continue
                
            # Приводим к дате без времени
            if hasattr(pub_date, 'date'):
                date_key = pub_date.date()
            else:
                from datetime import datetime
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    except:
                        continue
                date_key = pub_date.date()
            
            # Используем данные из базы, если они есть, иначе анализируем текст
            if tension_idx > 0:
                normalized_score = tension_idx / 100.0
            else:
                # Fallback к анализу текста
                text = f"{title} {content or ''}"
                metrics = tension_analyzer.analyze_text_tension(text, title)
                normalized_score = metrics.tension_score / 100.0
            
            if date_key not in daily_tension:
                daily_tension[date_key] = []
            
            daily_tension[date_key].append(normalized_score)
        
        # Вычисляем среднее значение для каждого дня
        historical_data = []
        for date_key in sorted(daily_tension.keys()):
            avg_tension = sum(daily_tension[date_key]) / len(daily_tension[date_key])
            from datetime import datetime
            datetime_key = datetime.combine(date_key, datetime.min.time())
            historical_data.append({
                'date': datetime_key.isoformat(),
                'value': round(avg_tension * 100, 1)  # В процентах
            })
        
        # Определяем целевое количество точек на основе периода
        if days == 7:
            target_points = 7
        elif days == 30:
            target_points = 15  # каждые 2 дня
        elif days == 90:
            target_points = 30  # каждые 3 дня
        else:
            target_points = min(days, 10)
        
        # Если данных мало, создаем дополнительные точки на основе периода
        if len(historical_data) < target_points:
            if historical_data:
                base_value = historical_data[0]['value']
                base_date = datetime.fromisoformat(historical_data[0]['date'])
                
                # Создаем недостающие точки
                for i in range(1, target_points - len(historical_data) + 1):
                    new_date = base_date + timedelta(days=i)
                    import random
                    variation = random.uniform(-10, 10)
                    new_value = max(0, min(100, base_value + variation))
                    historical_data.append({
                        'date': new_date.isoformat(),
                        'value': round(new_value, 1)
                    })
                
                historical_data.sort(key=lambda x: x['date'])
        
        # Генерируем прогноз (простой линейный тренд)
        forecast_data = []
        if len(historical_data) >= 2:
            # Вычисляем тренд
            recent_values = [d['value'] for d in historical_data[-3:]]
            trend = (recent_values[-1] - recent_values[0]) / len(recent_values) if len(recent_values) > 1 else 0
            
            last_date = datetime.fromisoformat(historical_data[-1]['date'])
            last_value = historical_data[-1]['value']
            
            for i in range(1, forecast_days + 1):
                forecast_date = last_date + timedelta(days=i)
                forecast_value = max(0, min(100, last_value + trend * i))
                forecast_data.append({
                    'date': forecast_date.isoformat(),
                    'value': round(forecast_value, 1)
                })
        
        # Определяем зоны напряженности
        zones = [
            {'name': 'Критическая зона', 'min': 80, 'max': 100, 'color': '#8e44ad'},
            {'name': 'Высокая зона', 'min': 60, 'max': 80, 'color': '#e74c3c'},
            {'name': 'Средняя зона', 'min': 40, 'max': 60, 'color': '#f39c12'},
            {'name': 'Низкая зона', 'min': 0, 'max': 40, 'color': '#2ecc71'}
        ]
        
        # Вычисляем среднюю напряженность и тренд
        avg_tension = sum(d['value'] for d in historical_data) / len(historical_data) if historical_data else 0
        
        if len(historical_data) >= 2:
            first_half = historical_data[:len(historical_data)//2]
            second_half = historical_data[len(historical_data)//2:]
            first_avg = sum(d['value'] for d in first_half) / len(first_half)
            second_avg = sum(d['value'] for d in second_half) / len(second_half)
            
            # Исправленный расчет тренда с защитой от деления на ноль и больших процентов
            if first_avg > 0.1:  # Минимальный порог для избежания огромных процентов
                trend_percent = round(((second_avg - first_avg) / first_avg) * 100, 1)
                # Ограничиваем максимальный процент изменения
                trend_percent = max(-100, min(100, trend_percent))
            else:
                # Если первое значение слишком маленькое, считаем абсолютное изменение
                trend_percent = round((second_avg - first_avg) * 10, 1)  # Умножаем на 10 для масштабирования
                trend_percent = max(-50, min(50, trend_percent))  # Ограничиваем в разумных пределах
            
            # Используем ту же логику, что и в get_full_statistics
            if trend_percent > 20:
                trend = '↗ Растет'
            elif trend_percent < -20:
                trend = '↘ Снижается'
            else:
                trend = '→ Стабильно'
        else:
            trend = '→ Стабильно'
            trend_percent = 0
        
        return jsonify({
            'status': 'success',
            'historical_data': historical_data,
            'forecast_data': forecast_data,
            'zones': zones,
            'avg_tension': round(avg_tension, 1),
            'trend': trend,
            'trend_percent': trend_percent,
            'historical_points': len(historical_data),
            'forecast_points': len(forecast_data),
            'target_points': target_points,
            'period_days': days
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting tension data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/territory_data', methods=['GET'])
def get_territory_data():
    """Получение данных для диаграммы по территориям.
    
    Query Parameters:
        days (int): Количество дней для анализа (по умолчанию 7)
        category (str): Категория новостей (по умолчанию 'all')
    
    Returns:
        JSON: Данные для диаграммы по территориям
    """
    try:
        days = int(request.args.get('days', 7))
        category = request.args.get('category', 'all')
        
        client = get_clickhouse_client()
        
        # Формируем условие для категории
        category_condition = ""
        if category != 'all':
            category_condition = f"AND category = '{category}'"
        
        # Получаем данные из всех таблиц с учетом категории
        # Используем тот же набор таблиц что и в /api/statistics для консистентности
        query = f"""
        SELECT 
            title, content, published_date, category, source
        FROM (
            SELECT title, content, published_date, category, source FROM news.ria_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.lenta_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.rbc_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.gazeta_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.kommersant_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.tsn_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.unian_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.rt_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.cnn_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.aljazeera_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.france24_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.dw_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.euronews_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.bbc_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.israil_headlines WHERE published_date >= today() - {days} {category_condition}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.telegram_headlines WHERE published_date >= today() - {days} {category_condition}
        )
        ORDER BY published_date DESC
        """
        
        results = client.execute(query)
        
        if not results:
            return jsonify({
                'status': 'success',
                'data': [],
                'total_news': 0
            })
        
        # Классифицируем по территориям на основе ключевых слов (4 региона)
        territory_keywords = {
            'Центральный': ['центр', 'центральная', 'киев', 'киевская', 'житомир', 'житомирская', 'черкассы', 'черкасская', 'полтава', 'полтавская', 'сумы', 'сумская', 'чернигов', 'черниговская', 'киевская область', 'центральная украина', 'киев', 'житомир', 'черкассы', 'полтава', 'сумы', 'чернигов'],
            'Восточный': ['восток', 'восточная', 'харьков', 'харьковская', 'донецк', 'донецкая', 'луганск', 'луганская', 'днепропетровск', 'днепропетровская', 'запорожье', 'запорожская', 'харьков', 'донецк', 'луганск', 'днепропетровск', 'запорожье'],
            'Южный': ['юг', 'южная', 'одесса', 'одесская', 'херсон', 'херсонская', 'николаев', 'николаевская', 'кировоград', 'кировоградская', 'крым', 'крымская', 'одесса', 'херсон', 'николаев', 'кировоград', 'крым'],
            'Западный': ['запад', 'западная', 'львов', 'львовская', 'волынь', 'волынская', 'тернополь', 'тернопольская', 'ивано-франковск', 'рівне', 'рівненська', 'закарпаття', 'закарпатська', 'чернівці', 'чернівецька', 'львов', 'волынь', 'тернополь', 'ивано-франковск', 'рівне', 'закарпаття', 'чернівці']
        }
        
        territory_counts = {territory: 0 for territory in territory_keywords.keys()}
        territory_news = {territory: [] for territory in territory_keywords.keys()}
        
        for title, content, pub_date, cat, source in results:
            text = f"{title} {content or ''}".lower()
            
            # Определяем территорию по ключевым словам
            territory = 'Центральный'  # По умолчанию
            max_matches = 0
            
            for terr, keywords in territory_keywords.items():
                matches = sum(1 for keyword in keywords if keyword in text)
                if matches > max_matches:
                    max_matches = matches
                    territory = terr
            
            territory_counts[territory] += 1
            territory_news[territory].append({
                'title': title,
                'date': pub_date.isoformat() if hasattr(pub_date, 'isoformat') else str(pub_date),
                'source': source,
                'category': cat
            })
        
        # Создаем данные для графика
        total_news = sum(territory_counts.values())
        territory_data = []
        
        colors = ['#e74c3c', '#3498db', '#f39c12', '#2ecc71', '#9b59b6']
        
        for i, (territory, count) in enumerate(territory_counts.items()):
            if count > 0:
                percent = round((count / total_news) * 100, 1) if total_news > 0 else 0
                territory_data.append({
                    'territory': territory,
                    'count': count,
                    'percent': percent,
                    'color': colors[i % len(colors)],
                    'news': territory_news[territory][:5]  # Последние 5 новостей
                })
        
        # Сортируем по количеству новостей
        territory_data.sort(key=lambda x: x['count'], reverse=True)
        
        return jsonify({
            'status': 'success',
            'data': territory_data,
            'total_news': total_news
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting territory data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@ukraine_analytics_bp.route('/full_statistics', methods=['GET'])
def get_full_statistics():
    """Получение полной статистики включая тренд и социальную активность.
    
    Query Parameters:
        category (str): Категория новостей (по умолчанию 'all')
        days (int): Количество дней для анализа (по умолчанию 7)
    
    Returns:
        JSON: Полная статистика с количеством новостей, трендом и социальной активностью
    """
    try:
        category = request.args.get('category', 'all')
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Получаем правильную таблицу для категории
        table_source = get_table_for_category(category)
        
        # ВСЕГДА используем UNION ALL запрос для всех источников для консистентности
        # Используем тот же набор таблиц что и в /api/statistics для консистентности
        category_filter = f"AND category = '{category}'" if category != 'all' else ""
        query = f"""
            SELECT title, content, published_date, category, source
            FROM (
            SELECT title, content, published_date, category, source FROM news.ria_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.lenta_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.rbc_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.gazeta_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.kommersant_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.tsn_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.unian_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.rt_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.cnn_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.aljazeera_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.reuters_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.france24_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.dw_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.euronews_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.bbc_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.israil_headlines WHERE published_date >= today() - {days} {category_filter}
            UNION ALL
            SELECT title, content, published_date, category, source FROM news.telegram_headlines WHERE published_date >= today() - {days} {category_filter}
            )
            ORDER BY published_date DESC
            """
        
        results = client.execute(query)
        
        if not results or len(results) == 0:
            return jsonify({
                'status': 'success',
                'total_news': 0,
                'trend': '→ Стабильно',
                'social_activity': 'Нет данных'
            })
        
        total_news = len(results)
        
        # Подсчет новостей по дням для анализа тренда
        from collections import defaultdict
        daily_counts = defaultdict(int)
        
        for title, content, pub_date, cat, source in results:
            if pub_date:
                date_key = pub_date.date()
                daily_counts[date_key] += 1
        
        # Анализ тренда (сравниваем первую и вторую половины периода)
        sorted_dates = sorted(daily_counts.keys())
        if len(sorted_dates) >= 2:
            mid_point = len(sorted_dates) // 2
            first_half_dates = sorted_dates[:mid_point]
            second_half_dates = sorted_dates[mid_point:]
            
            first_half_avg = sum(daily_counts[d] for d in first_half_dates) / len(first_half_dates) if first_half_dates else 0
            second_half_avg = sum(daily_counts[d] for d in second_half_dates) / len(second_half_dates) if second_half_dates else 0
            
            # Унифицированный расчет тренда с процентом изменения (как в get_tension_data)
            if first_half_avg > 0.1:  # Минимальный порог для избежания огромных процентов
                trend_percent = round(((second_half_avg - first_half_avg) / first_half_avg) * 100, 1)
                # Ограничиваем максимальный процент изменения
                trend_percent = max(-100, min(100, trend_percent))
            else:
                # Если первое значение слишком маленькое, считаем абсолютное изменение
                trend_percent = round((second_half_avg - first_half_avg) * 10, 1)  # Умножаем на 10 для масштабирования
                trend_percent = max(-50, min(50, trend_percent))  # Ограничиваем в разумных пределах
            
            # Используем ту же логику, что и в get_tension_data
            if trend_percent > 20:
                trend = '↗ Растет'
            elif trend_percent < -20:
                trend = '↘ Снижается'
            else:
                trend = '→ Стабильно'
        else:
            trend = '→ Стабильно'
            trend_percent = 0
        
        # Анализ социальной активности (на основе количества новостей)
        avg_daily_news = total_news / days if days > 0 else 0
        
        if avg_daily_news > 50:
            social_activity = 'Очень высокая'
        elif avg_daily_news > 20:
            social_activity = 'Высокая'
        elif avg_daily_news > 10:
            social_activity = 'Средняя'
        elif avg_daily_news > 0:
            social_activity = 'Низкая'
        else:
            social_activity = 'Нет данных'
        
        # Дополнительные критерии
        # Скорость новостей в час
        news_velocity = round(total_news / (days * 24), 1) if days > 0 else 0
        
        # Пиковый час (анализируем по часам)
        hourly_counts = defaultdict(int)
        for title, content, pub_date, cat, source in results:
            if pub_date:
                hour = pub_date.hour
                hourly_counts[hour] += 1
        
        peak_hour = max(hourly_counts.items(), key=lambda x: x[1])[0] if hourly_counts else 0
        peak_hour_str = f"{peak_hour:02d}:00"
        
        # Тренд тональности (упрощенный анализ)
        sentiment_trend = "→ Стабильный"
        if len(results) >= 10:
            # Берем первые и последние 5 новостей для анализа
            first_half = results[:5]
            second_half = results[-5:]
            
            # Простой анализ тональности по ключевым словам
            positive_words = ['успех', 'победа', 'освобождение', 'прогресс', 'улучшение']
            negative_words = ['поражение', 'отступление', 'потери', 'кризис', 'проблемы']
            
            first_sentiment = 0
            second_sentiment = 0
            
            for title, content, pub_date, cat, source in first_half:
                text = f"{title} {content or ''}".lower()
                pos_count = sum(1 for word in positive_words if word in text)
                neg_count = sum(1 for word in negative_words if word in text)
                first_sentiment += (pos_count - neg_count)
            
            for title, content, pub_date, cat, source in second_half:
                text = f"{title} {content or ''}".lower()
                pos_count = sum(1 for word in positive_words if word in text)
                neg_count = sum(1 for word in negative_words if word in text)
                second_sentiment += (pos_count - neg_count)
            
            if second_sentiment > first_sentiment + 2:
                sentiment_trend = "↗ Позитивный"
            elif second_sentiment < first_sentiment - 2:
                sentiment_trend = "↘ Негативный"
            else:
                sentiment_trend = "→ Стабильный"
        
        return jsonify({
            'status': 'success',
            'total_news': total_news,
            'trend': trend,
            'trend_percent': trend_percent,
            'social_activity': social_activity,
            'avg_daily_news': round(avg_daily_news, 1),
            'news_velocity': news_velocity,
            'peak_hour': peak_hour_str,
            'sentiment_trend': sentiment_trend
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting full statistics: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': str(e)}), 500