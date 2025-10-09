"""API РґР»СЏ СЂР°Р±РѕС‚С‹ СЃ РЅРѕРІРѕСЃС‚СЏРјРё.

Р­С‚РѕС‚ РјРѕРґСѓР»СЊ СЃРѕРґРµСЂР¶РёС‚ REST API СЌРЅРґРїРѕРёРЅС‚С‹ РґР»СЏ:
- РџРѕР»СѓС‡РµРЅРёСЏ РЅРѕРІРѕСЃС‚РµР№ РёР· СЂР°Р·Р»РёС‡РЅС‹С… РёСЃС‚РѕС‡РЅРёРєРѕРІ
- Р¤РёР»СЊС‚СЂР°С†РёРё РїРѕ РєР°С‚РµРіРѕСЂРёСЏРј Рё РёСЃС‚РѕС‡РЅРёРєР°Рј
- РџРѕРёСЃРєР° РїРѕ СЃРѕРґРµСЂР¶РёРјРѕРјСѓ
- РџРѕР»СѓС‡РµРЅРёСЏ СЃС‚Р°С‚РёСЃС‚РёРєРё
"""

from flask import Blueprint, request, jsonify
import datetime
from app.models import get_clickhouse_client

# РЎРѕР·РґР°РµРј Blueprint РґР»СЏ API РЅРѕРІРѕСЃС‚РµР№
news_api_bp = Blueprint('news_api', __name__, url_prefix='/api')

@news_api_bp.route('/news', methods=['GET'])
def get_news():
    """РџРѕР»СѓС‡РµРЅРёРµ РЅРѕРІРѕСЃС‚РµР№ СЃ С„РёР»СЊС‚СЂР°С†РёРµР№ Рё РїРѕРёСЃРєРѕРј.
    
    Query Parameters:
        source (str): РСЃС‚РѕС‡РЅРёРє РЅРѕРІРѕСЃС‚РµР№ ('all', 'ria', 'israil', 'telegram', 'lenta', 'rbc', 'cnn', 'aljazeera', 'tsn', 'unian', 'rt', 'euronews', 'reuters', 'france24', 'dw', 'bbc', 'gazeta', 'kommersant')
        category (str): РљР°С‚РµРіРѕСЂРёСЏ РЅРѕРІРѕСЃС‚РµР№ ('all', 'ukraine', 'middle_east', etc.)
        limit (int): РљРѕР»РёС‡РµСЃС‚РІРѕ РЅРѕРІРѕСЃС‚РµР№ РґР»СЏ РІРѕР·РІСЂР°С‚Р° (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 100)
        offset (int): РЎРјРµС‰РµРЅРёРµ РґР»СЏ РїР°РіРёРЅР°С†РёРё (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 0)
        search (str): РџРѕРёСЃРєРѕРІС‹Р№ Р·Р°РїСЂРѕСЃ РїРѕ Р·Р°РіРѕР»РѕРІРєСѓ Рё СЃРѕРґРµСЂР¶РёРјРѕРјСѓ
    
    Returns:
        JSON: РЎРїРёСЃРѕРє РЅРѕРІРѕСЃС‚РµР№ СЃ РјРµС‚Р°РґР°РЅРЅС‹РјРё РёР»Рё СЃРѕРѕР±С‰РµРЅРёРµ РѕР± РѕС€РёР±РєРµ
    """
    source = request.args.get('source', 'universal_military_operations')
    category = request.args.get('category', 'all')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    search = request.args.get('search', '')
    
    # Проверка валидности источников
    valid_sources = ['all', 'ria', 'israil', 'telegram', 'twitter', 'lenta', 'rbc', 'cnn', 'aljazeera', 'tsn', 'unian', 'rt', 'euronews', 'reuters', 'france24', 'dw', 'bbc', 'gazeta', 'kommersant', 'universal_military_operations', 'universal_humanitarian_crisis', 'universal_economic_consequences', 'universal_political_decisions', 'universal_information_social']
    
    if source not in valid_sources:
        return jsonify({'status': 'error', 'message': f'РќРµРґРѕРїСѓСЃС‚РёРјС‹Р№ РёСЃС‚РѕС‡РЅРёРє. Р”РѕРїСѓСЃС‚РёРјС‹Рµ РёСЃС‚РѕС‡РЅРёРєРё: {valid_sources}'}), 400
    
    # РџСЂРѕРІРµСЂРєР° РІР°Р»РёРґРЅРѕСЃС‚Рё РєР°С‚РµРіРѕСЂРёРё (РІРєР»СЋС‡Р°СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ С‚Р°Р±Р»РёС†С‹)
    valid_categories = ['military_operations', 'humanitarian_crisis', 'economic_consequences', 'political_decisions', 'information_social', 'diplomatic_efforts']
    
    # РџСЂРѕРІРµСЂСЏРµРј, СЏРІР»СЏРµС‚СЃСЏ Р»Рё РєР°С‚РµРіРѕСЂРёСЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРѕР№ С‚Р°Р±Р»РёС†РµР№
    is_custom_table = category.startswith('custom_') and category.endswith('_headlines')
    
    if category not in valid_categories and category != 'all' and not is_custom_table:
        return jsonify({'status': 'error', 'message': f'РќРµРґРѕРїСѓСЃС‚РёРјР°СЏ РєР°С‚РµРіРѕСЂРёСЏ. Р”РѕРїСѓСЃС‚РёРјС‹Рµ РєР°С‚РµРіРѕСЂРёРё: {valid_categories} РёР»Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ С‚Р°Р±Р»РёС†С‹'}), 400
    
    try:
        client = get_clickhouse_client()
        
        # РџРѕР»СѓС‡Р°РµРј СЃРїРёСЃРѕРє РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёС… С‚Р°Р±Р»РёС† РґР»СЏ РІРєР»СЋС‡РµРЅРёСЏ РІ РѕР±С‰РёР№ Р·Р°РїСЂРѕСЃ
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
                SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                FROM news.{table_name}
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
            """
            custom_tables_unions.append(union_query)
        
        # Р¤РѕСЂРјРёСЂСѓРµРј Р·Р°РїСЂРѕСЃ РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ РёСЃС‚РѕС‡РЅРёРєР° Рё РєР°С‚РµРіРѕСЂРёРё
        if source.startswith('universal_'):
            # Р Р°Р±РѕС‚Р° СЃ universal С‚Р°Р±Р»РёС†Р°РјРё
            table_name = source
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, '' as link,
                    '' as telegram_channel
                FROM news.{table_name}
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'all' and category == 'all':
            # Все источники, все категории
            # Для Telegram используем таблицу telegram_headlines
            telegram_union_query = '''
                SELECT id, title, message_link as link, content, source, category, published_date, message_link, channel 
                FROM news.telegram_headlines
            '''
            
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date,
                    CASE
                        WHEN source = 'ria.ru' THEN link
                        WHEN source = '7kanal.co.il' THEN link
                        WHEN source = 'telegram' THEN message_link
                        ELSE link
                    END as link,
                    if(source = 'telegram', channel, '') as telegram_channel
                FROM (
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.ria_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.israil_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.lenta_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.rbc_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.cnn_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.aljazeera_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.tsn_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.unian_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.rt_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.euronews_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.reuters_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.france24_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.dw_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.bbc_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.gazeta_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                    FROM news.kommersant_headlines
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    
                    UNION ALL
                    
                    SELECT id, title, '' as link, content, source, category, published_date, message_link, channel
                    FROM (
                        {telegram_union_query}
                    )
                    {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                )
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'all' and category != 'all':
            # Все источники, конкретная категория
            # Проверяем, какие таблицы категорий существуют
            check_tables_query = f"""
                SELECT name 
                FROM system.tables 
                WHERE database = 'news' 
                AND (name = 'telegram_{category}' 
                    OR name = 'israil_{category}'
                    OR name = 'ria_{category}'
                    OR name = 'lenta_{category}'
                    OR name = 'rbc_{category}'
                    OR name = 'cnn_{category}'
                    OR name = 'aljazeera_{category}'
                    OR name = 'tsn_{category}'
                    OR name = 'unian_{category}'
                    OR name = 'rt_{category}'
                    OR name = 'euronews_{category}'
                    OR name = 'reuters_{category}'
                    OR name = 'france24_{category}'
                    OR name = 'dw_{category}'
                    OR name = 'bbc_{category}'
                    OR name = 'gazeta_{category}'
                    OR name = 'kommersant_{category}'
                    OR name = 'universal_{category}'
                    OR name = 'ukraine_universal_{category}')
            """
            
            existing_tables_result = client.query(check_tables_query)
            existing_tables = [row[0] for row in existing_tables_result.result_rows]
            
            unions = []
            
            # Добавляем запросы только для существующих таблиц
            for table_name in existing_tables:
                if table_name.startswith('telegram_'):
                    unions.append(f'''
                        SELECT id, title, '' as link, content, source, category, published_date, message_link, channel
                        FROM news.{table_name}
                        {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    ''')
                else:
                    unions.append(f'''
                    SELECT id, title, link, content, source, category, published_date, '' as message_link, '' as channel
                        FROM news.{table_name}
                        {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                    ''')
            
            # Если нет ни одной таблицы, возвращаем пустой результат
            if not unions:
                return jsonify({
                    'status': 'success',
                    'data': [],
                    'total': 0,
                    'limit': limit,
                    'offset': offset,
                    'current_page': 1,
                    'total_pages': 0
                })
            
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date,
                    CASE
                        WHEN source = 'ria.ru' THEN link
                        WHEN source = '7kanal.co.il' THEN link
                        WHEN source = 'telegram' THEN message_link
                        ELSE link
                    END as link,
                    if(source = 'telegram', channel, '') as telegram_channel
                FROM (
                    {' UNION ALL '.join(unions)}
                )
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'ria' and category == 'all':
            # РўРѕР»СЊРєРѕ Р РРђ, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.ria_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'ria' and category != 'all':
            # РўРѕР»СЊРєРѕ Р РРђ, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.ria_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'israil' and category == 'all':
            # РўРѕР»СЊРєРѕ РР·СЂР°РёР»СЊ, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.israil_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'israil' and category != 'all':
            # РўРѕР»СЊРєРѕ РР·СЂР°РёР»СЊ, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.israil_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'telegram' and category == 'all':
            # Только Telegram, все категории - читаем из telegram_headlines
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, message_link as link,
                    channel as telegram_channel
                FROM news.telegram_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'telegram' and category != 'all':
            # Только Telegram, конкретная категория - фильтруем по category
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, message_link as link,
                    channel as telegram_channel
                FROM news.telegram_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'lenta' and category == 'all':
            # РўРѕР»СЊРєРѕ Lenta, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.lenta_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'lenta' and category != 'all':
            # РўРѕР»СЊРєРѕ Lenta, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.lenta_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'rbc' and category == 'all':
            # РўРѕР»СЊРєРѕ RBC, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.rbc_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'rbc' and category != 'all':
            # РўРѕР»СЊРєРѕ RBC, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.rbc_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'cnn' and category == 'all':
            # РўРѕР»СЊРєРѕ CNN, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.cnn_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'cnn' and category != 'all':
            # РўРѕР»СЊРєРѕ CNN, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.cnn_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'aljazeera' and category == 'all':
            # РўРѕР»СЊРєРѕ Al Jazeera, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.aljazeera_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'aljazeera' and category != 'all':
            # РўРѕР»СЊРєРѕ Al Jazeera, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.aljazeera_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'tsn' and category == 'all':
            # РўРѕР»СЊРєРѕ TSN, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.tsn_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'tsn' and category != 'all':
            # РўРѕР»СЊРєРѕ TSN, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.tsn_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'unian' and category == 'all':
            # РўРѕР»СЊРєРѕ UNIAN, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.unian_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'unian' and category != 'all':
            # РўРѕР»СЊРєРѕ UNIAN, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.unian_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'rt' and category == 'all':
            # РўРѕР»СЊРєРѕ RT, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.rt_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'rt' and category != 'all':
            # РўРѕР»СЊРєРѕ RT, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.rt_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'euronews' and category == 'all':
            # РўРѕР»СЊРєРѕ Euronews, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.euronews_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'euronews' and category != 'all':
            # РўРѕР»СЊРєРѕ Euronews, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.euronews_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'reuters' and category == 'all':
            # РўРѕР»СЊРєРѕ Reuters, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.reuters_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'reuters' and category != 'all':
            # РўРѕР»СЊРєРѕ Reuters, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.reuters_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'france24' and category == 'all':
            # РўРѕР»СЊРєРѕ France24, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.france24_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'france24' and category != 'all':
            # РўРѕР»СЊРєРѕ France24, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.france24_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'dw' and category == 'all':
            # РўРѕР»СЊРєРѕ DW, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.dw_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'dw' and category != 'all':
            # РўРѕР»СЊРєРѕ DW, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.dw_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'bbc' and category == 'all':
            # РўРѕР»СЊРєРѕ BBC, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.bbc_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'bbc' and category != 'all':
            # РўРѕР»СЊРєРѕ BBC, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.bbc_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'gazeta' and category == 'all':
            # РўРѕР»СЊРєРѕ Gazeta, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.gazeta_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'gazeta' and category != 'all':
            # РўРѕР»СЊРєРѕ Gazeta, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.gazeta_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'kommersant' and category == 'all':
            # РўРѕР»СЊРєРѕ Kommersant, РІСЃРµ РєР°С‚РµРіРѕСЂРёРё
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.kommersant_headlines
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'kommersant' and category != 'all':
            # РўРѕР»СЊРєРѕ Kommersant, РєРѕРЅРєСЂРµС‚РЅР°СЏ РєР°С‚РµРіРѕСЂРёСЏ
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.kommersant_headlines
                WHERE category = '{category}' {f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')" if search else ""}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif is_custom_table:
            # РџРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєР°СЏ С‚Р°Р±Р»РёС†Р°
            query = f'''
                SELECT 
                    id, title, content, source, category, published_date, link,
                    '' as telegram_channel
                FROM news.{category}
                {f"WHERE title ILIKE '%{search}%' OR content ILIKE '%{search}%'" if search else "WHERE 1=1"}
                ORDER BY published_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        else:
            return jsonify({'status': 'error', 'message': 'РќРµРґРѕРїСѓСЃС‚РёРјС‹Р№ РёСЃС‚РѕС‡РЅРёРє'}), 400
            
        result = client.query(query)
        
        # Р¤РѕСЂРјР°С‚РёСЂСѓРµРј РґР°РЅРЅС‹Рµ
        news = []
        for row in result.result_rows:
            news_item = {
                'id': str(row[0]),
                'title': row[1],
                'content': row[2],
                'source': row[3],
                'category': row[4],
                'published_date': row[5].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row[5], 'strftime') else row[5]
            }
            
            # Р”РѕР±Р°РІР»СЏРµРј СЃРїРµС†РёС„РёС‡РЅС‹Рµ РїРѕР»СЏ РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ РёСЃС‚РѕС‡РЅРёРєР°
            if len(row) > 6 and row[6]:  # link
                news_item['link'] = row[6]
            if len(row) > 7 and row[7]:  # telegram_channel
                news_item['telegram_channel'] = row[7]
                
            news.append(news_item)
        
        # РџРѕРґСЃС‡РµС‚ РѕР±С‰РµРіРѕ РєРѕР»РёС‡РµСЃС‚РІР° Р·Р°РїРёСЃРµР№
        count_query = f'''
            SELECT COUNT(*) as count
            FROM (
                {query.split('ORDER BY')[0]}
            ) as subquery
        '''
        total_count = client.query(count_query).result_rows[0][0]
        
        # Р Р°СЃС‡РµС‚ РѕР±С‰РµРіРѕ РєРѕР»РёС‡РµСЃС‚РІР° СЃС‚СЂР°РЅРёС†
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
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in get_news API:")
        print(f"Category: {category}, Source: {source}")
        print(f"Error: {str(e)}")
        print(f"Traceback:\n{error_details}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@news_api_bp.route('/social_media', methods=['GET'])
def get_social_media_data():
    """РџРѕР»СѓС‡РµРЅРёРµ РґР°РЅРЅС‹С… РёР· СЃРѕС†РёР°Р»СЊРЅС‹С… СЃРµС‚РµР№.
    
    Query Parameters:
        source (str): РСЃС‚РѕС‡РЅРёРє ('twitter', 'vk', 'ok', 'all')
        page (int): РќРѕРјРµСЂ СЃС‚СЂР°РЅРёС†С‹ (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 1)
        days (int): РљРѕР»РёС‡РµСЃС‚РІРѕ РґРЅРµР№ РґР»СЏ РІС‹Р±РѕСЂРєРё (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 7)
        search (str): РџРѕРёСЃРєРѕРІС‹Р№ Р·Р°РїСЂРѕСЃ
    
    Returns:
        JSON: Р”Р°РЅРЅС‹Рµ РёР· СЃРѕС†РёР°Р»СЊРЅС‹С… СЃРµС‚РµР№
    """
    try:
        source = request.args.get('source', 'all')
        page = int(request.args.get('page', 1))
        days = int(request.args.get('days', 7))
        search = request.args.get('search', '')
        page_size = 20
        
        client = get_clickhouse_client()
        
        # РћРїСЂРµРґРµР»СЏРµРј С‚Р°Р±Р»РёС†С‹ РґР»СЏ Р·Р°РїСЂРѕСЃР°
        tables = []
        if source == 'all':
            tables = ['twitter_posts', 'vk_posts', 'ok_posts']
        elif source == 'twitter':
            tables = ['twitter_posts']
        elif source == 'vk':
            tables = ['vk_posts']
        elif source == 'ok':
            tables = ['ok_posts']
        else:
            return jsonify({'status': 'error', 'message': 'РќРµРїРѕРґРґРµСЂР¶РёРІР°РµРјС‹Р№ РёСЃС‚РѕС‡РЅРёРє'}), 400
        
        # Р¤РѕСЂРјРёСЂСѓРµРј UNION Р·Р°РїСЂРѕСЃ РґР»СЏ РІСЃРµС… С‚Р°Р±Р»РёС†
        union_queries = []
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        for table in tables:
            # РџСЂРѕРІРµСЂСЏРµРј СЃСѓС‰РµСЃС‚РІРѕРІР°РЅРёРµ С‚Р°Р±Р»РёС†С‹
            check_table_query = f"""
                SELECT count() FROM system.tables 
                WHERE database = 'news' AND name = '{table}'
            """
            table_exists = client.query(check_table_query).result_rows[0][0] > 0
            
            if table_exists:
                search_condition = ""
                if search:
                    search_condition = f"AND (title ILIKE '%{search}%' OR content ILIKE '%{search}%')"
                
                union_query = f"""
                    SELECT 
                        id, title, content, source, published_date,
                        CASE 
                            WHEN source = 'twitter' THEN post_url
                            WHEN source = 'vk' THEN post_url
                            WHEN source = 'ok' THEN post_url
                            ELSE ''
                        END as post_url,
                        CASE 
                            WHEN source = 'twitter' THEN author
                            WHEN source = 'vk' THEN group_name
                            WHEN source = 'ok' THEN group_name
                            ELSE ''
                        END as author_or_group,
                        CASE 
                            WHEN source = 'twitter' THEN likes_count
                            WHEN source = 'vk' THEN likes_count
                            WHEN source = 'ok' THEN likes_count
                            ELSE 0
                        END as engagement
                    FROM news.{table}
                    WHERE published_date >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'
                    {search_condition}
                """
                union_queries.append(union_query)
        
        if not union_queries:
            return jsonify({
                'status': 'success',
                'data': [],
                'total': 0,
                'page': page,
                'total_pages': 0
            })
        
        # РћР±СЉРµРґРёРЅСЏРµРј Р·Р°РїСЂРѕСЃС‹ Рё РґРѕР±Р°РІР»СЏРµРј РїР°РіРёРЅР°С†РёСЋ
        full_query = " UNION ALL ".join(union_queries)
        full_query += f"""
            ORDER BY published_date DESC
            LIMIT {page_size} OFFSET {(page - 1) * page_size}
        """
        
        result = client.query(full_query)
        
        # РџРѕР»СѓС‡Р°РµРј РѕР±С‰РµРµ РєРѕР»РёС‡РµСЃС‚РІРѕ Р·Р°РїРёСЃРµР№ РґР»СЏ РїР°РіРёРЅР°С†РёРё
        count_query = " UNION ALL ".join([q.replace("SELECT id, title, content, source, published_date, CASE WHEN source = 'twitter' THEN post_url WHEN source = 'vk' THEN post_url WHEN source = 'ok' THEN post_url ELSE '' END as post_url, CASE WHEN source = 'twitter' THEN author WHEN source = 'vk' THEN group_name WHEN source = 'ok' THEN group_name ELSE '' END as author_or_group, CASE WHEN source = 'twitter' THEN likes_count WHEN source = 'vk' THEN likes_count WHEN source = 'ok' THEN likes_count ELSE 0 END as engagement", "SELECT count() as total") for q in union_queries])
        count_result = client.query(f"SELECT sum(total) FROM ({count_query})")
        total_count = count_result.result_rows[0][0] if count_result.result_rows else 0
        
        # Р¤РѕСЂРјР°С‚РёСЂСѓРµРј РґР°РЅРЅС‹Рµ
        posts = []
        for row in result.result_rows:
            posts.append({
                'id': str(row[0]),
                'title': row[1] or '',
                'content': row[2] or '',
                'source': row[3],
                'published_date': row[4].strftime('%Y-%m-%d %H:%M:%S') if row[4] else '',
                'post_url': row[5] or '',
                'author_or_group': row[6] or '',
                'engagement': row[7] or 0
            })
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return jsonify({
            'status': 'success',
            'data': posts,
            'total': total_count,
            'page': page,
            'total_pages': total_pages,
            'source': source
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'РћС€РёР±РєР° РїСЂРё РїРѕР»СѓС‡РµРЅРёРё РґР°РЅРЅС‹С… СЃРѕС†РёР°Р»СЊРЅС‹С… СЃРµС‚РµР№: {str(e)}'
        }), 500
    finally:
        if 'client' in locals():
            client.close()

@news_api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """РџРѕР»СѓС‡РµРЅРёРµ СЃС‚Р°С‚РёСЃС‚РёРєРё РїРѕ РєРѕР»РёС‡РµСЃС‚РІСѓ СЃС‚Р°С‚РµР№.
    
    Р’РѕР·РІСЂР°С‰Р°РµС‚ РѕР±С‰РµРµ РєРѕР»РёС‡РµСЃС‚РІРѕ СЃС‚Р°С‚РµР№ Рё СЂР°Р·Р±РёРІРєСѓ РїРѕ РєР°С‚РµРіРѕСЂРёСЏРј
    РґР»СЏ РѕС‚РѕР±СЂР°Р¶РµРЅРёСЏ РЅР° РіР»Р°РІРЅРѕР№ СЃС‚СЂР°РЅРёС†Рµ.
    
    Returns:
        JSON: РЎС‚Р°С‚РёСЃС‚РёРєР° РїРѕ РєРѕР»РёС‡РµСЃС‚РІСѓ СЃС‚Р°С‚РµР№
    """
    try:
        client = get_clickhouse_client()
        
        # РџРѕР»СѓС‡Р°РµРј РѕР±С‰РµРµ РєРѕР»РёС‡РµСЃС‚РІРѕ СЃС‚Р°С‚РµР№ РёР· РІСЃРµС… РёСЃС‚РѕС‡РЅРёРєРѕРІ
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
                SELECT id FROM news.telegram_headlines
            )
        """
        
        total_result = client.query(total_query)
        total_count = total_result.result_rows[0][0] if total_result.result_rows else 0
        
        # РџРѕР»СѓС‡Р°РµРј СЃС‚Р°С‚РёСЃС‚РёРєСѓ РїРѕ РєР°С‚РµРіРѕСЂРёСЏРј
        categories_stats = {}
        
        categories = {
            'military_operations': 'Военные операции',
            'humanitarian_crisis': 'Гуманитарный кризис',
            'economic_consequences': 'Экономические последствия',
            'political_decisions': 'Политические решения',
            'information_social': 'Информационно-социальные аспекты'
        }
        
        # РџРѕР»СѓС‡Р°РµРј СЃРїРёСЃРѕРє РІСЃРµС… СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёС… С‚Р°Р±Р»РёС† РІ СЃС…РµРјРµ news
        existing_tables_query = """
            SELECT name FROM system.tables 
            WHERE database = 'news'
            ORDER BY name
        """
        existing_tables_result = client.query(existing_tables_query)
        existing_tables = {row[0] for row in existing_tables_result.result_rows}
        
        for category_key, category_name in categories.items():
            # РЎРїРёСЃРѕРє РёСЃС‚РѕС‡РЅРёРєРѕРІ РґР»СЏ РїСЂРѕРІРµСЂРєРё
            sources = ['ria', 'lenta', 'rbc', 'gazeta', 'kommersant', 'tsn', 'unian', 'rt', 
                      'cnn', 'aljazeera', 'reuters', 'france24', 'dw', 'euronews', 'bbc', 'israil']
            
            # РЎС‚СЂРѕРёРј Р·Р°РїСЂРѕСЃ С‚РѕР»СЊРєРѕ РґР»СЏ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёС… С‚Р°Р±Р»РёС†
            # Считаем ТОЛЬКО из _headlines таблиц, так как они содержат все данные
            union_parts = []
            
            # Добавляем основные таблицы _headlines с фильтром по category
            for source in sources:
                table_name = f"{source}_headlines"
                if table_name in existing_tables:
                    union_parts.append(f"SELECT id FROM news.{table_name} WHERE category = '{category_key}'")
            
            # Добавляем telegram_headlines с фильтром по category
            if 'telegram_headlines' in existing_tables:
                union_parts.append(f"SELECT id FROM news.telegram_headlines WHERE category = '{category_key}'")
            
            if union_parts:
                category_query = f"""
                    SELECT COUNT(*) as count FROM (
                        {' UNION ALL '.join(union_parts)}
                    )
                """
                category_result = client.query(category_query)
                category_count = category_result.result_rows[0][0] if category_result.result_rows else 0
            else:
                category_count = 0
                
            categories_stats[category_key] = {
                'name': category_name,
                'count': category_count
            }
        
        # РџРѕР»СѓС‡Р°РµРј СЃС‚Р°С‚РёСЃС‚РёРєСѓ РїРѕ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРј С‚Р°Р±Р»РёС†Р°Рј
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

@news_api_bp.route('/categories', methods=['GET'])
def get_categories():
    """РџРѕР»СѓС‡РµРЅРёРµ СЃРїРёСЃРєР° РґРѕСЃС‚СѓРїРЅС‹С… РєР°С‚РµРіРѕСЂРёР№ РЅРѕРІРѕСЃС‚РµР№, РІРєР»СЋС‡Р°СЏ РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ СЃР°Р№С‚С‹.
    
    Returns:
        JSON: РЎРїРёСЃРѕРє РєР°С‚РµРіРѕСЂРёР№ СЃ РёС… РЅР°Р·РІР°РЅРёСЏРјРё Рё С‚РёРїР°РјРё
    """
    try:
        client = get_clickhouse_client()
        
        # Р‘Р°Р·РѕРІС‹Рµ РєР°С‚РµРіРѕСЂРёРё
        base_categories = [
            {'id': 'all', 'name': 'Все категории', 'type': 'base'},
            {'id': 'military_operations', 'name': 'Военные операции', 'type': 'base'},
        {'id': 'humanitarian_crisis', 'name': 'Гуманитарный кризис', 'type': 'base'},
        {'id': 'economic_consequences', 'name': 'Экономические последствия', 'type': 'base'},
        {'id': 'political_decisions', 'name': 'Политические решения', 'type': 'base'},
        {'id': 'information_social', 'name': 'Информационно-социальные аспекты', 'type': 'base'}
        ]
        
        # РџРѕР»СѓС‡Р°РµРј РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ С‚Р°Р±Р»РёС†С‹
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
            # РР·РІР»РµРєР°РµРј РЅР°Р·РІР°РЅРёРµ СЃР°Р№С‚Р° РёР· РёРјРµРЅРё С‚Р°Р±Р»РёС†С‹
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

# API-СЌРЅРґРїРѕРёРЅС‚ РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ РґР°РЅРЅС‹С… РёР· telegram_headlines
@news_api_bp.route('/telegram', methods=['GET'])
def get_telegram_headlines():
    """РџРѕР»СѓС‡РµРЅРёРµ Р·Р°РіРѕР»РѕРІРєРѕРІ РЅРѕРІРѕСЃС‚РµР№ РёР· Telegram РєР°РЅР°Р»РѕРІ СЃ РїР°РіРёРЅР°С†РёРµР№.
    
    Query Parameters:
        page (int): РќРѕРјРµСЂ СЃС‚СЂР°РЅРёС†С‹ РґР»СЏ РїР°РіРёРЅР°С†РёРё (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 1)
        channel (str): Р¤РёР»СЊС‚СЂ РїРѕ РєРѕРЅРєСЂРµС‚РЅРѕРјСѓ РєР°РЅР°Р»Сѓ (РѕРїС†РёРѕРЅР°Р»СЊРЅРѕ)
        days (int): РљРѕР»РёС‡РµСЃС‚РІРѕ РґРЅРµР№ РґР»СЏ РІС‹Р±РѕСЂРєРё (РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ 7)
    
    Returns:
        JSON: РЎРїРёСЃРѕРє Р·Р°РіРѕР»РѕРІРєРѕРІ Telegram РЅРѕРІРѕСЃС‚РµР№ СЃ РјРµС‚Р°РґР°РЅРЅС‹РјРё РїР°РіРёРЅР°С†РёРё
    """
    try:
        page = int(request.args.get('page', 1))
        page_size = 10  # РљРѕР»РёС‡РµСЃС‚РІРѕ Р·Р°РїРёСЃРµР№ РЅР° СЃС‚СЂР°РЅРёС†Рµ
        channel = request.args.get('channel', None)
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Р‘Р°Р·РѕРІС‹Р№ Р·Р°РїСЂРѕСЃ
        query = '''
            SELECT id, title, content, channel, message_id, message_link, published_date
            FROM (
                SELECT id, title, content, channel, message_id, message_link, published_date FROM news.telegram_ukraine
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, published_date FROM news.telegram_middle_east
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, published_date FROM news.telegram_fake_news
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, published_date FROM news.telegram_info_war
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, published_date FROM news.telegram_europe
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, published_date FROM news.telegram_usa
                UNION ALL
                SELECT id, title, content, channel, message_id, message_link, published_date FROM news.telegram_other
            )
            WHERE published_date >= %(start_date)s
        '''
        
        # Р”РѕР±Р°РІР»СЏРµРј С„РёР»СЊС‚СЂ РїРѕ РєР°РЅР°Р»Сѓ, РµСЃР»Рё СѓРєР°Р·Р°РЅ
        if channel:
            query += ' AND channel = %(channel)s'
            
        query += '''
            ORDER BY published_date DESC
            LIMIT %(limit)s OFFSET %(offset)s
        '''
        
        # РџР°СЂР°РјРµС‚СЂС‹ Р·Р°РїСЂРѕСЃР°
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        params = {
            'start_date': start_date,
            'limit': page_size,
            'offset': (page - 1) * page_size
        }
        
        if channel:
            params['channel'] = channel
            
        result = client.query(query, parameters=params)
        
        # Р¤РѕСЂРјР°С‚РёСЂСѓРµРј РґР°РЅРЅС‹Рµ
        headlines = [
            {
                'id': str(row[0]),
                'title': row[1],
                'content': row[2],
                'channel': row[3],
                'message_id': row[4],
                'message_link': row[5],
                'published_date': row[6].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row[6], 'strftime') else row[6]
            }
            for row in result.result_rows
        ]
        
        # РџРѕРґСЃС‡РµС‚ РѕР±С‰РµРіРѕ РєРѕР»РёС‡РµСЃС‚РІР° Р·Р°РїРёСЃРµР№ РґР»СЏ РїР°РіРёРЅР°С†РёРё
        count_query = '''
            SELECT COUNT(*)
            FROM (
                SELECT id FROM news.telegram_ukraine WHERE published_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_middle_east WHERE published_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_fake_news WHERE published_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_info_war WHERE published_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_europe WHERE published_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_usa WHERE published_date >= %(start_date)s
                UNION ALL
                SELECT id FROM news.telegram_other WHERE published_date >= %(start_date)s
            )
        '''
        
        if channel:
            count_query += ' AND channel = %(channel)s'
            
        total_count = client.query(count_query, parameters=params).result_rows[0][0]
        total_pages = (total_count + page_size - 1) // page_size
        
        # РџРѕР»СѓС‡Р°РµРј СЃРїРёСЃРѕРє РґРѕСЃС‚СѓРїРЅС‹С… РєР°РЅР°Р»РѕРІ РґР»СЏ С„РёР»СЊС‚СЂР°С†РёРё
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

@news_api_bp.route('/sources', methods=['GET'])
def get_available_sources():
    """РџРѕР»СѓС‡РµРЅРёРµ СЃРїРёСЃРєР° РІСЃРµС… РґРѕСЃС‚СѓРїРЅС‹С… РёСЃС‚РѕС‡РЅРёРєРѕРІ РґР°РЅРЅС‹С….
    
    Р’РѕР·РІСЂР°С‰Р°РµС‚ СЃРїРёСЃРѕРє РІСЃРµС… РґРѕСЃС‚СѓРїРЅС‹С… РёСЃС‚РѕС‡РЅРёРєРѕРІ РЅРѕРІРѕСЃС‚РµР№,
    РІРєР»СЋС‡Р°СЏ СЃС‚Р°РЅРґР°СЂС‚РЅС‹Рµ РёСЃС‚РѕС‡РЅРёРєРё Рё РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ С‚Р°Р±Р»РёС†С‹.
    
    Returns:
        JSON: РЎРїРёСЃРѕРє РґРѕСЃС‚СѓРїРЅС‹С… РёСЃС‚РѕС‡РЅРёРєРѕРІ СЃ РёС… РѕРїРёСЃР°РЅРёСЏРјРё
    """
    try:
        client = get_clickhouse_client()
        
        # РЎС‚Р°РЅРґР°СЂС‚РЅС‹Рµ РёСЃС‚РѕС‡РЅРёРєРё
        standard_sources = {
            'all': 'Все категории',
            'ria': 'Р РРђ РќРѕРІРѕСЃС‚Рё',
            'lenta': 'Lenta.ru',
            'rbc': 'Р Р‘Рљ',
            'gazeta': 'Р“Р°Р·РµС‚Р°.ru',
            'kommersant': 'РљРѕРјРјРµСЂСЃР°РЅС‚СЉ',
            'tsn': 'РўРЎРќ',
            'unian': 'РЈРќРРђРќ',
            'rt': 'RT',
            'cnn': 'CNN',
            'aljazeera': 'Al Jazeera',
            'reuters': 'Reuters',
            'france24': 'France 24',
            'dw': 'Deutsche Welle',
            'euronews': 'Euronews',
            'bbc': 'BBC',
            'israil': '7kanal.co.il',
            'telegram': 'Telegram РєР°РЅР°Р»С‹'
        }
        
        # РџРѕР»СѓС‡Р°РµРј СЃРїРёСЃРѕРє РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёС… С‚Р°Р±Р»РёС†
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
            # РР·РІР»РµРєР°РµРј РЅР°Р·РІР°РЅРёРµ СЃР°Р№С‚Р° РёР· РёРјРµРЅРё С‚Р°Р±Р»РёС†С‹
            site_name = table_name.replace('custom_', '').replace('_headlines', '')
            display_name = site_name.replace('_', '.').title()
            custom_sources[table_name] = f'РџРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёР№ СЃР°Р№С‚: {display_name}'
        
        # РЎС‚Р°РЅРґР°СЂС‚РЅС‹Рµ РєР°С‚РµРіРѕСЂРёРё
        standard_categories = {
            'all': 'Все категории',
            'ukraine': 'РЈРєСЂР°РёРЅР°',
            'middle_east': 'Р‘Р»РёР¶РЅРёР№ Р’РѕСЃС‚РѕРє',
            'fake_news': 'Р¤РµР№РєРѕРІС‹Рµ РЅРѕРІРѕСЃС‚Рё',
            'info_war': 'РРЅС„РѕСЂРјР°С†РёРѕРЅРЅР°СЏ РІРѕР№РЅР°',
            'europe': 'Р•РІСЂРѕРїР°',
            'usa': 'РЎРЁРђ',
            'other': 'Р”СЂСѓРіРѕРµ'
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
