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
        source (str): Источник новостей ('all', 'ria', 'israil', 'telegram', 'lenta', 'rbc', 'cnn', 'aljazeera', 'tsn', 'unian', 'rt', 'euronews', 'reuters', 'france24', 'dw', 'bbc', 'gazeta', 'kommersant')
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
    
    # Проверка валидности категории (включая пользовательские таблицы)
    valid_categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
    
    # Проверяем, является ли категория пользовательской таблицей
    is_custom_table = category.startswith('custom_') and category.endswith('_headlines')
    
    if category not in valid_categories and category != 'all' and not is_custom_table:
        return jsonify({'status': 'error', 'message': f'Недопустимая категория. Допустимые категории: {valid_categories} или пользовательские таблицы'}), 400
    
    try:
        client = get_clickhouse_client()
        
        # Получаем список пользовательских таблиц для включения в общий запрос
        custom_tables_query = """
            SELECT name 
            FROM system.tables 
            WHERE database = 'news' 
            AND name LIKE 'custom_%_headlines'
        """
        custom_tables = client.query(custom_tables_query)
        custom_tables_unions = []
        
        for table in custom_tables.result_rows:
            table_name = table[0]
            union_query = f"""
                SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                FROM news.{table_name}
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
            """
            custom_tables_unions.append(union_query)
        
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
                        ELSE link
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
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.lenta_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.rbc_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.cnn_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.aljazeera_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.tsn_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.unian_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.rt_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.euronews_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.reuters_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.france24_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.dw_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.bbc_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.gazeta_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.kommersant_headlines
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
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.universal_ukraine
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.universal_middle_east
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.universal_fake_news
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.universal_info_war
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.universal_europe
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.universal_usa
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.universal_other
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
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.lenta_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.rbc_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.cnn_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.aljazeera_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.tsn_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.unian_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.rt_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.euronews_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.reuters_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.france24_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.dw_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.bbc_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.gazeta_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.kommersant_headlines
                    WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, '' as link, content, source, category, parsed_date, message_link, channel
                    FROM (
                        SELECT id, title, content, source, category, parsed_date, message_link, channel FROM news.telegram_{category}
                    )
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as message_link, '' as channel
                    FROM news.universal_{category}
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
        elif source == 'lenta' and category == 'all':
            # Только Lenta, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.lenta_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'lenta' and category != 'all':
            # Только Lenta, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.lenta_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'rbc' and category == 'all':
            # Только RBC, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.rbc_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'rbc' and category != 'all':
            # Только RBC, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.rbc_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'cnn' and category == 'all':
            # Только CNN, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.cnn_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'cnn' and category != 'all':
            # Только CNN, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.cnn_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'aljazeera' and category == 'all':
            # Только Al Jazeera, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.aljazeera_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'aljazeera' and category != 'all':
            # Только Al Jazeera, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.aljazeera_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'tsn' and category == 'all':
            # Только TSN, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.tsn_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'tsn' and category != 'all':
            # Только TSN, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.tsn_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'unian' and category == 'all':
            # Только UNIAN, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.unian_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'unian' and category != 'all':
            # Только UNIAN, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.unian_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'rt' and category == 'all':
            # Только RT, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.rt_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'rt' and category != 'all':
            # Только RT, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.rt_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'euronews' and category == 'all':
            # Только Euronews, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.euronews_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'euronews' and category != 'all':
            # Только Euronews, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.euronews_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'reuters' and category == 'all':
            # Только Reuters, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.reuters_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'reuters' and category != 'all':
            # Только Reuters, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.reuters_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'france24' and category == 'all':
            # Только France24, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.france24_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'france24' and category != 'all':
            # Только France24, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.france24_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'dw' and category == 'all':
            # Только DW, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.dw_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'dw' and category != 'all':
            # Только DW, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.dw_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'bbc' and category == 'all':
            # Только BBC, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.bbc_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'bbc' and category != 'all':
            # Только BBC, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.bbc_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'gazeta' and category == 'all':
            # Только Gazeta, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.gazeta_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'gazeta' and category != 'all':
            # Только Gazeta, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.gazeta_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'kommersant' and category == 'all':
            # Только Kommersant, все категории
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.kommersant_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'kommersant' and category != 'all':
            # Только Kommersant, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.kommersant_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif is_custom_table:
            # Пользовательская таблица
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date, link,
                    '' as telegram_channel
                FROM news.{category}
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

@news_api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Получение статистики по количеству статей.
    
    Возвращает общее количество статей и разбивку по категориям
    для отображения на главной странице.
    
    Returns:
        JSON: Статистика по количеству статей
    """
    try:
        client = get_clickhouse_client()
        
        # Получаем общее количество статей из всех источников (включая старые)
        total_query = """
            SELECT COUNT(*) as total FROM (
                SELECT id FROM news.ria_headlines
                UNION ALL
                SELECT id FROM news.lenta_headlines
                UNION ALL
                SELECT id FROM news.rbc_headlines
                UNION ALL
                SELECT id FROM news.gazeta_headlines
                UNION ALL
                SELECT id FROM news.kommersant_headlines
                UNION ALL
                SELECT id FROM news.tsn_headlines
                UNION ALL
                SELECT id FROM news.unian_headlines
                UNION ALL
                SELECT id FROM news.rt_headlines
                UNION ALL
                SELECT id FROM news.cnn_headlines
                UNION ALL
                SELECT id FROM news.aljazeera_headlines
                UNION ALL
                SELECT id FROM news.reuters_headlines
                UNION ALL
                SELECT id FROM news.france24_headlines
                UNION ALL
                SELECT id FROM news.dw_headlines
                UNION ALL
                SELECT id FROM news.euronews_headlines
                UNION ALL
                SELECT id FROM news.bbc_headlines
                UNION ALL
                SELECT id FROM news.israil_headlines
                UNION ALL
                SELECT id FROM news.telegram_ukraine
                UNION ALL
                SELECT id FROM news.telegram_middle_east
                UNION ALL
                SELECT id FROM news.telegram_fake_news
                UNION ALL
                SELECT id FROM news.telegram_info_war
                UNION ALL
                SELECT id FROM news.telegram_europe
                UNION ALL
                SELECT id FROM news.telegram_usa
                UNION ALL
                SELECT id FROM news.telegram_other
                UNION ALL
                SELECT id FROM news.universal_ukraine
                UNION ALL
                SELECT id FROM news.universal_middle_east
                UNION ALL
                SELECT id FROM news.universal_fake_news
                UNION ALL
                SELECT id FROM news.universal_info_war
                UNION ALL
                SELECT id FROM news.universal_europe
                UNION ALL
                SELECT id FROM news.universal_usa
                UNION ALL
                SELECT id FROM news.universal_other
            )
        """
        
        total_result = client.query(total_query)
        total_count = total_result.result_rows[0][0] if total_result.result_rows else 0
        
        # Получаем статистику по категориям
        categories_stats = {}
        
        categories = {
            'ukraine': 'Украина',
            'middle_east': 'Ближний Восток', 
            'fake_news': 'Фейки',
            'info_war': 'Инфовойна',
            'europe': 'Европа',
            'usa': 'США',
            'other': 'Другое'
        }
        
        for category_key, category_name in categories.items():
            category_query = f"""
                SELECT COUNT(*) as count FROM (
                    SELECT id FROM news.ria_{category_key}
                    UNION ALL
                    SELECT id FROM news.lenta_{category_key}
                    UNION ALL
                    SELECT id FROM news.rbc_{category_key}
                    UNION ALL
                    SELECT id FROM news.gazeta_{category_key}
                    UNION ALL
                    SELECT id FROM news.kommersant_{category_key}
                    UNION ALL
                    SELECT id FROM news.tsn_{category_key}
                    UNION ALL
                    SELECT id FROM news.unian_{category_key}
                    UNION ALL
                    SELECT id FROM news.rt_{category_key}
                    UNION ALL
                    SELECT id FROM news.cnn_{category_key}
                    UNION ALL
                    SELECT id FROM news.aljazeera_{category_key}
                    UNION ALL
                    SELECT id FROM news.reuters_{category_key}
                    UNION ALL
                    SELECT id FROM news.france24_{category_key}
                    UNION ALL
                    SELECT id FROM news.dw_{category_key}
                    UNION ALL
                    SELECT id FROM news.euronews_{category_key}
                    UNION ALL
                    SELECT id FROM news.bbc_{category_key}
                    UNION ALL
                    SELECT id FROM news.israil_{category_key}
                    UNION ALL
                    SELECT id FROM news.telegram_{category_key}
                    UNION ALL
                    SELECT id FROM news.universal_{category_key}
                )
            """
            
            category_result = client.query(category_query)
            category_count = category_result.result_rows[0][0] if category_result.result_rows else 0
            categories_stats[category_key] = {
                'name': category_name,
                'count': category_count
            }
        
        # Получаем статистику по пользовательским таблицам
        custom_tables_query = """
            SELECT name FROM system.tables 
            WHERE database = 'news' 
            AND name LIKE 'custom_%_headlines'
            ORDER BY name
        """
        
        custom_tables_result = client.query(custom_tables_query)
        custom_stats = {}
        
        for row in custom_tables_result.result_rows:
            table_name = row[0]
            site_name = table_name.replace('custom_', '').replace('_headlines', '')
            display_name = site_name.replace('_', '.').title()
            
            custom_count_query = f"SELECT COUNT(*) FROM news.{table_name}"
            custom_count_result = client.query(custom_count_query)
            custom_count = custom_count_result.result_rows[0][0] if custom_count_result.result_rows else 0
            
            custom_stats[table_name] = {
                'name': display_name,
                'count': custom_count
            }
        
        return jsonify({
            'status': 'success',
            'data': {
                'total': total_count,
                'categories': categories_stats,
                'custom_sources': custom_stats
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'client' in locals():
            client.close()

@news_api_bp.route('/categories', methods=['GET'])
def get_categories():
    """Получение списка доступных категорий новостей, включая пользовательские сайты.
    
    Returns:
        JSON: Список категорий с их названиями и типами
    """
    try:
        client = get_clickhouse_client()
        
        # Базовые категории
        base_categories = [
            {'id': 'all', 'name': 'Все категории', 'type': 'base'},
            {'id': 'ukraine', 'name': 'Украина', 'type': 'base'},
            {'id': 'middle_east', 'name': 'Ближний восток', 'type': 'base'},
            {'id': 'fake_news', 'name': 'Фейки', 'type': 'base'},
            {'id': 'info_war', 'name': 'Инфовойна', 'type': 'base'},
            {'id': 'europe', 'name': 'Европа', 'type': 'base'},
            {'id': 'usa', 'name': 'США', 'type': 'base'},
            {'id': 'other', 'name': 'Другое', 'type': 'base'}
        ]
        
        # Получаем пользовательские таблицы
        custom_tables_query = """
            SELECT name 
            FROM system.tables 
            WHERE database = 'news' 
            AND name LIKE 'custom_%_headlines'
        """
        
        custom_tables = client.query(custom_tables_query)
        custom_categories = []
        
        for table in custom_tables.result_rows:
            table_name = table[0]
            # Извлекаем название сайта из имени таблицы
            site_name = table_name.replace('custom_', '').replace('_headlines', '').replace('_', '.')
            custom_categories.append({
                'id': table_name,
                'name': site_name.title(),
                'type': 'custom',
                'table_name': table_name
            })
        
        all_categories = base_categories + custom_categories
        
        return jsonify({
            'status': 'success',
            'data': all_categories,
            'total': len(all_categories)
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

@news_api_bp.route('/sources', methods=['GET'])
def get_available_sources():
    """Получение списка всех доступных источников данных.
    
    Возвращает список всех доступных источников новостей,
    включая стандартные источники и пользовательские таблицы.
    
    Returns:
        JSON: Список доступных источников с их описаниями
    """
    try:
        client = get_clickhouse_client()
        
        # Стандартные источники
        standard_sources = {
            'all': 'Все источники',
            'ria': 'РИА Новости',
            'lenta': 'Lenta.ru',
            'rbc': 'РБК',
            'gazeta': 'Газета.ru',
            'kommersant': 'Коммерсантъ',
            'tsn': 'ТСН',
            'unian': 'УНИАН',
            'rt': 'RT',
            'cnn': 'CNN',
            'aljazeera': 'Al Jazeera',
            'reuters': 'Reuters',
            'france24': 'France 24',
            'dw': 'Deutsche Welle',
            'euronews': 'Euronews',
            'bbc': 'BBC',
            'israil': '7kanal.co.il',
            'telegram': 'Telegram каналы'
        }
        
        # Получаем список пользовательских таблиц
        custom_tables_query = """
            SELECT name FROM system.tables 
            WHERE database = 'news' 
            AND name LIKE 'custom_%_headlines'
            ORDER BY name
        """
        
        custom_tables_result = client.query(custom_tables_query)
        custom_sources = {}
        
        for row in custom_tables_result.result_rows:
            table_name = row[0]
            # Извлекаем название сайта из имени таблицы
            site_name = table_name.replace('custom_', '').replace('_headlines', '')
            display_name = site_name.replace('_', '.').title()
            custom_sources[table_name] = f'Пользовательский сайт: {display_name}'
        
        # Стандартные категории
        standard_categories = {
            'all': 'Все категории',
            'ukraine': 'Украина',
            'middle_east': 'Ближний Восток',
            'fake_news': 'Фейковые новости',
            'info_war': 'Информационная война',
            'europe': 'Европа',
            'usa': 'США',
            'other': 'Другое'
        }
        
        return jsonify({
            'status': 'success',
            'data': {
                'sources': {
                    'standard': standard_sources,
                    'custom': custom_sources
                },
                'categories': standard_categories
            }
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'client' in locals():
            client.close()