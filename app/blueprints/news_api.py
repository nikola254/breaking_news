"""API для работы с новостями.

Этот модуль содержит REST API эндпоинты для:
- Получения новостей из различных источников
- Фильтрации по категориям и источникам
- Поиска по содержимому
- Получения статистики
"""

from flask import Blueprint, request, jsonify
import datetime
from app.models import get_clickhouse_client

# Создаем Blueprint для API новостей
news_api_bp = Blueprint('news_api', __name__, url_prefix='/api')

@news_api_bp.route('/news', methods=['GET'])
def get_news():
    """Получение новостей с фильтрацией и поиском.
    
    Query Parameters:
        source (str): Источник новостей ('all', 'ria', 'israil', 'telegram')
        category (str): Категория новостей ('all', 'ukraine', 'middle_east', etc.)
        limit (int): Количество новостей для возврата (по умолчанию 100)
        offset (int): Смещение для пагинации (по умолчанию 0)
        search (str): Поисковый запрос по заголовку и содержимому
    
    Returns:
        JSON: Список новостей с метаданными или сообщение об ошибке
    """
    source = request.args.get('source', 'all')
    category = request.args.get('category', 'all')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    search = request.args.get('search', '')
    
    # Проверка валидности категории
    valid_categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
    if category not in valid_categories and category != 'all':
        return jsonify({'status': 'error', 'message': f'Недопустимая категория. Допустимые категории: {valid_categories}'}), 400
    
    try:
        client = get_clickhouse_client()
        
        # Формируем запрос в зависимости от источника и категории
        if source == 'all' and category == 'all':
            # Все источники, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date,
                    CASE
                        WHEN source = 'ria.ru' THEN link
                        WHEN source = '7kanal.co.il' THEN link
                        WHEN source = 'telegram' THEN message_link
                        ELSE ''
                    END as link,
                    if(source = 'telegram', channel, '') as telegram_channel
                FROM (
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.ria_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.israil_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, '' as link, content, source, category, parsed_date, message_link, channel
                    FROM (
                        SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_ukraine
                        UNION ALL
                        SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_middle_east
                        UNION ALL
                        SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_fake_news
                        UNION ALL
                        SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_info_war
                        UNION ALL
                        SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_europe
                        UNION ALL
                        SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_usa
                        UNION ALL
                        SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_other
                    )
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                )
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'all' and category != 'all':
            # Все источники, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date,
                    CASE
                        WHEN source = 'ria.ru' THEN link
                        WHEN source = '7kanal.co.il' THEN link
                        WHEN source = 'telegram' THEN message_link
                        ELSE ''
                    END as link,
                    if(source = 'telegram', channel, '') as telegram_channel
                FROM (
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.ria_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.israil_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, '' as link, content, source, category, parsed_date, message_link, channel
                    FROM (
                        SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_{category}
                    )
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                )
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'ria' and category == 'all':
            # Только РИА, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.ria_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'ria' and category != 'all':
            # Только РИА, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.ria_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'israil' and category == 'all':
            # Только Израиль, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.israil_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'israil' and category != 'all':
            # Только Израиль, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.israil_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'telegram' and category == 'all':
            # Только Telegram, все категории
            query = f'''
                SELECT 
                    id, title, message_link as link, content, source, category, parsed_date,
                    channel as telegram_channel
                FROM (
                    SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_ukraine
                    UNION ALL
                    SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_middle_east
                    UNION ALL
                    SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_fake_news
                    UNION ALL
                    SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_info_war
                    UNION ALL
                    SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_europe
                    UNION ALL
                    SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_usa
                    UNION ALL
                    SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_other
                )
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'telegram' and category != 'all':
            # Только Telegram, конкретная категория
            query = f'''
                SELECT 
                    id, title, message_link as link, content, source, category, parsed_date,
                    channel as telegram_channel
                FROM news.telegram_{category}
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        else:
            return jsonify({'status': 'error', 'message': 'Недопустимый источник'}), 400
            
        result = client.query(query)
        
        # Форматируем данные
        news = []
        for row in result.result_rows:
            news_item = {
                'id': str(row[0]),
                'title': row[1],
                'content': row[2],
                'source': row[3],
                'category': row[4],
                'parsed_date': row[5].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row[5], 'strftime') else row[5]
            }
            
            # Добавляем специфичные поля в зависимости от источника
            if len(row) > 6 and row[6]:  # link
                news_item['link'] = row[6]
            if len(row) > 7 and row[7]:  # telegram_channel
                news_item['telegram_channel'] = row[7]
                
            news.append(news_item)
        
        # Подсчет общего количества записей
        count_query = f'''
            SELECT COUNT(*) as count
            FROM (
                {query.split('ORDER BY')[0]}
            ) as subquery
        '''
        total_count = client.query(count_query).result_rows[0][0]
        
        # Расчет общего количества страниц
        page_size = limit
        total_pages = (total_count + page_size - 1) // page_size
        current_page = (offset // page_size) + 1

        return jsonify({
            'status': 'success',
            'data': news,
            'total_count': total_count,
            'total_pages': total_pages,
            'current_page': current_page,
            'page_size': page_size
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'client' in locals():
            client.close()

# API-эндпоинт для получения данных из telegram_headlines
@news_api_bp.route('/telegram', methods=['GET'])
def get_telegram_headlines():
    """Получение заголовков новостей из Telegram каналов с пагинацией.
    
    Query Parameters:
        page (int): Номер страницы для пагинации (по умолчанию 1)
        channel (str): Фильтр по конкретному каналу (опционально)
        days (int): Количество дней для выборки (по умолчанию 7)
    
    Returns:
        JSON: Список заголовков Telegram новостей с метаданными пагинации
    """
    try:
        page = int(request.args.get('page', 1))
        page_size = 10  # Количество записей на странице
        channel = request.args.get('channel', None)
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Базовый запрос
        query = '''
            SELECT id, title, content, channel, message_id, message_link, parsed_date
            FROM (
                SELECT id, title, content, channel, message_id, message_link, parsed_date FROM news.telegram_ukraine
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, parsed_date FROM news.telegram_middle_east
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, parsed_date FROM news.telegram_fake_news
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, parsed_date FROM news.telegram_info_war
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, parsed_date FROM news.telegram_europe
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, parsed_date FROM news.telegram_usa
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, parsed_date FROM news.telegram_other
            )
            WHERE parsed_date >= %(start_date)s
        '''
        
        # Добавляем фильтр по каналу, если указан
        if channel:
            query += ' AND channel = %(channel)s'
            
        query += '''
            ORDER BY parsed_date DESC
            LIMIT %(limit)s OFFSET %(offset)s
        '''
        
        # Параметры запроса
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        params = {
            'start_date': start_date,
            'limit': page_size,
            'offset': (page - 1) * page_size
        }
        
        if channel:
            params['channel'] = channel
            
        result = client.query(query, parameters=params)
        
        # Форматируем данные
        headlines = [
            {
                'id': str(row[0]),
                'title': row[1],
                'content': row[2],
                'channel': row[3],
                'message_id': row[4],
                'message_link': row[5],
                'parsed_date': row[6].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row[6], 'strftime') else row[6]
            }
            for row in result.result_rows
        ]
        
        # Подсчет общего количества записей для пагинации
        count_query = '''
            SELECT COUNT(*)
            FROM (
                SELECT id FROM news.telegram_ukraine WHERE parsed_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_middle_east WHERE parsed_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_fake_news WHERE parsed_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_info_war WHERE parsed_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_europe WHERE parsed_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_usa WHERE parsed_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_other WHERE parsed_date >= %(start_date)s
            )
        '''
        
        if channel:
            count_query += ' AND channel = %(channel)s'
            
        total_count = client.query(count_query, parameters=params).result_rows[0][0]
        total_pages = (total_count + page_size - 1) // page_size
        
        # Получаем список доступных каналов для фильтрации
        channels_query = '''
            SELECT DISTINCT channel FROM (
                SELECT channel FROM news.telegram_ukraine
                UNION ALL
                SELECT channel FROM news.telegram_middle_east
                UNION ALL
                SELECT channel FROM news.telegram_fake_news
                UNION ALL
                SELECT channel FROM news.telegram_info_war
                UNION ALL
                SELECT channel FROM news.telegram_europe
                UNION ALL
                SELECT channel FROM news.telegram_usa
                UNION ALL
                SELECT channel FROM news.telegram_other
            ) ORDER BY channel
        '''
        channels = [row[0] for row in client.query(channels_query).result_rows]
        
        return jsonify({
            'status': 'success',
            'data': headlines,
            'total_pages': total_pages,
            'current_page': page,
            'available_channels': channels
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'client' in locals():
            client.close()