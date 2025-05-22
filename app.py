from flask import Flask, jsonify, request, render_template
import clickhouse_connect
import datetime

app = Flask(__name__, static_folder='static', static_url_path='')

# Настройки ClickHouse
CLICKHOUSE_HOST = 'localhost'
CLICKHOUSE_PORT = 8123
CLICKHOUSE_USER = 'default'
CLICKHOUSE_PASSWORD = ''

# Подключение к ClickHouse
def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD
    )

# API-эндпоинт для получения новостей
@app.route('/api/news', methods=['GET'])
def get_news():
    source = request.args.get('source', 'all')
    category = request.args.get('category', 'all')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
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
                    if(source = 'ria.ru', link, '') as link,
                    if(source = '7kanal.co.il', link, '') as israil_link,
                    if(source = '7kanal.co.il', source_links, '') as source_links,
                    if(source = 'telegram', message_link, '') as telegram_link,
                    if(source = 'telegram', channel, '') as telegram_channel
                FROM (
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.ria_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, source_links, '' as message_link, '' as channel
                    FROM news.israil_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, '' as link, content, source, category, parsed_date, '' as source_links, message_link, channel
                    FROM news.telegram_headlines
                )
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'all' and category != 'all':
            # Все источники, конкретная категория
            query = f'''
                SELECT 
                    id, title, content, source, category, parsed_date,
                    if(source = 'ria.ru', link, '') as link,
                    if(source = '7kanal.co.il', link, '') as israil_link,
                    if(source = '7kanal.co.il', source_links, '') as source_links,
                    if(source = 'telegram', message_link, '') as telegram_link,
                    if(source = 'telegram', channel, '') as telegram_channel
                FROM (
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.ria_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, source_links, '' as message_link, '' as channel
                    FROM news.israil_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, '' as link, content, source, category, parsed_date, '' as source_links, message_link, channel
                    FROM news.telegram_headlines
                    WHERE category = '{category}'
                )
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'ria' and category == 'all':
            # Только РИА, все категории
            query = f'''
                SELECT 
                    id, title, link as link, content, source, category, parsed_date,
                    '' as israil_link, '' as source_links, '' as telegram_link, '' as telegram_channel
                FROM news.ria_headlines
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'ria' and category != 'all':
            # Только РИА, конкретная категория
            query = f'''
                SELECT 
                    id, title, link as link, content, source, category, parsed_date,
                    '' as israil_link, '' as source_links, '' as telegram_link, '' as telegram_channel
                FROM news.ria_headlines
                WHERE category = '{category}'
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'israil' and category == 'all':
            # Только Израиль, все категории
            query = f'''
                SELECT 
                    id, title, '' as link, content, source, category, parsed_date,
                    link as israil_link, source_links, '' as telegram_link, '' as telegram_channel
                FROM news.israil_headlines
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'israil' and category != 'all':
            # Только Израиль, конкретная категория
            query = f'''
                SELECT 
                    id, title, '' as link, content, source, category, parsed_date,
                    link as israil_link, source_links, '' as telegram_link, '' as telegram_channel
                FROM news.israil_headlines
                WHERE category = '{category}'
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'telegram' and category == 'all':
            # Только Telegram, все категории
            query = f'''
                SELECT 
                    id, title, '' as link, content, source, category, parsed_date,
                    '' as israil_link, '' as source_links, message_link as telegram_link, channel as telegram_channel
                FROM news.telegram_headlines
                ORDER BY parsed_date DESC
                LIMIT {limit} OFFSET {offset}
            '''
        elif source == 'telegram' and category != 'all':
            # Только Telegram, конкретная категория
            query = f'''
                SELECT 
                    id, title, '' as link, content, source, category, parsed_date,
                    '' as israil_link, '' as source_links, message_link as telegram_link, channel as telegram_channel
                FROM news.telegram_headlines
                WHERE category = '{category}'
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
                'parsed_date': row[5].strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # Добавляем специфичные поля в зависимости от источника
            if row[6]:  # link для РИА
                news_item['link'] = row[6]
            if row[7]:  # israil_link
                news_item['israil_link'] = row[7]
            if row[8]:  # source_links
                news_item['source_links'] = row[8]
            if row[9]:  # telegram_link
                news_item['telegram_link'] = row[9]
            if row[10]:  # telegram_channel
                news_item['telegram_channel'] = row[10]
                
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

# API-эндпоинт для запуска парсеров
@app.route('/api/run_parser', methods=['POST'])
def run_parser():
    try:
        data = request.json
        source = data.get('source', 'all')
        
        # Импортируем необходимые модули
        import threading
        import subprocess
        
        # Обрабатываем случай, когда источники переданы в виде строки с разделителями
        if isinstance(source, str) and ',' in source:
            sources = source.split(',')
        else:
            sources = [source]
        
        # Определяем, какой парсер запустить в зависимости от источника
        if 'telegram' in sources or 'all' in sources:
            # Запускаем парсер Telegram в отдельном потоке
            def run_telegram_parser():
                subprocess.run(['python', 'parser_telegram.py'])
            
            thread = threading.Thread(target=run_telegram_parser)
            thread.daemon = True
            thread.start()
        
        if 'israil' in sources or 'all' in sources:
            # Запускаем парсер Израиль в отдельном потоке
            def run_israil_parser():
                subprocess.run(['python', 'parser_israil.py'])
            
            thread = threading.Thread(target=run_israil_parser)
            thread.daemon = True
            thread.start()
        
        if 'ria' in sources or 'all' in sources:
            # Запускаем парсер РИА в отдельном потоке
            def run_ria_parser():
                subprocess.run(['python', 'parser_ria.py'])
            
            thread = threading.Thread(target=run_ria_parser)
            thread.daemon = True
            thread.start()
        
        return jsonify({
            'status': 'success',
            'message': f'Парсер для источника {source} успешно запущен'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# API-эндпоинт для генерации прогноза
@app.route('/api/generate_forecast', methods=['POST'])
def generate_forecast():
    try:
        data = request.json
        model = data.get('model', 'lstm')
        source = data.get('source', 'all')
        period = data.get('period', 7)
        
        # Здесь будет код для генерации прогноза
        # В реальном приложении здесь будет вызов соответствующих моделей
        
        # Пример данных для ответа
        import datetime
        import random
        
        # Генерируем случайные данные для примера
        today = datetime.datetime.now()
        tension_values = []
        for i in range(period):
            date = today + datetime.timedelta(days=i)
            value = random.uniform(0.3, 0.8)
            tension_values.append({
                'date': date.strftime('%d.%m.%Y'),
                'value': value,
                'lower_bound': max(0, value - random.uniform(0.05, 0.15)),
                'upper_bound': min(1, value + random.uniform(0.05, 0.15))
            })
        
        topics = [
            {'name': 'Политика', 'value': random.uniform(0.2, 0.4), 'change': random.uniform(-0.1, 0.1)},
            {'name': 'Экономика', 'value': random.uniform(0.1, 0.3), 'change': random.uniform(-0.1, 0.1)},
            {'name': 'Военные действия', 'value': random.uniform(0.2, 0.5), 'change': random.uniform(-0.1, 0.1)},
            {'name': 'Международные отношения', 'value': random.uniform(0.1, 0.2), 'change': random.uniform(-0.1, 0.1)},
            {'name': 'Другое', 'value': random.uniform(0.05, 0.15), 'change': random.uniform(-0.05, 0.05)}
        ]
        
        # Формируем ответ
        response = {
            'status': 'success',
            'tension_forecast': {
                'chart_url': '/plots/test_tension_forecast_20250508_171336.png',
                'values': tension_values
            },
            'topics_forecast': {
                'chart_url': '/plots/test_tension_forecast_20250508_173232.png',
                'topics': topics
            }
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# API-эндпоинт для получения данных из telegram_headlines
@app.route('/api/telegram', methods=['GET'])
def get_telegram_headlines():
    try:
        page = int(request.args.get('page', 1))
        page_size = 10  # Количество записей на странице
        channel = request.args.get('channel', None)
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Базовый запрос
        query = '''
            SELECT id, title, content, channel, message_id, message_link, parsed_date
            FROM news.telegram_headlines
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
                'parsed_date': row[6].strftime('%Y-%m-%d %H:%M:%S')
            }
            for row in result.result_rows
        ]
        
        # Подсчет общего количества записей для пагинации
        count_query = '''
            SELECT COUNT(*)
            FROM news.telegram_headlines
            WHERE parsed_date >= %(start_date)s
        '''
        
        if channel:
            count_query += ' AND channel = %(channel)s'
            
        total_count = client.query(count_query, parameters=params).result_rows[0][0]
        total_pages = (total_count + page_size - 1) // page_size
        
        # Получаем список доступных каналов для фильтрации
        channels_query = 'SELECT DISTINCT channel FROM news.telegram_headlines ORDER BY channel'
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
        client.close()

# API-эндпоинт для получения данных из israil_headlines
@app.route('/api/israil', methods=['GET'])
def get_israil_headlines():
    try:
        page = int(request.args.get('page', 1))
        page_size = 10  # Количество записей на странице
        category = request.args.get('category', None)
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Базовый запрос
        query = '''
            SELECT id, title, link, content, source_links, source, category, parsed_date
            FROM news.israil_headlines
            WHERE parsed_date >= %(start_date)s
        '''
        
        # Добавляем фильтр по категории, если указана
        if category:
            query += ' AND category = %(category)s'
            
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
        
        if category:
            params['category'] = category
            
        result = client.query(query, parameters=params)
        
        # Форматируем данные
        headlines = [
            {
                'id': str(row[0]),
                'title': row[1],
                'link': row[2],
                'content': row[3],
                'source_links': row[4],
                'source': row[5],
                'category': row[6],
                'parsed_date': row[7].strftime('%Y-%m-%d %H:%M:%S')
            }
            for row in result.result_rows
        ]
        
        # Подсчет общего количества записей для пагинации
        count_query = '''
            SELECT COUNT(*)
            FROM news.israil_headlines
            WHERE parsed_date >= %(start_date)s
        '''
        
        if category:
            count_query += ' AND category = %(category)s'
            
        total_count = client.query(count_query, parameters=params).result_rows[0][0]
        total_pages = (total_count + page_size - 1) // page_size
        
        # Получаем список доступных категорий для фильтрации
        categories_query = 'SELECT DISTINCT category FROM news.israil_headlines ORDER BY category'
        categories = [row[0] for row in client.query(categories_query).result_rows]
        
        return jsonify({
            'status': 'success',
            'data': headlines,
            'total_pages': total_pages,
            'current_page': page,
            'available_categories': categories
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        client.close()

# API-эндпоинт для получения данных из ria_headlines
@app.route('/api/ria', methods=['GET'])
def get_ria_headlines():
    try:
        page = int(request.args.get('page', 1))
        page_size = 10  # Количество записей на странице
        category = request.args.get('category', None)
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Базовый запрос
        query = '''
            SELECT id, title, link, content, source, category, parsed_date
            FROM news.ria_headlines
            WHERE parsed_date >= %(start_date)s
        '''
        
        # Добавляем фильтр по категории, если указана
        if category:
            query += ' AND category = %(category)s'
            
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
        
        if category:
            params['category'] = category
            
        result = client.query(query, parameters=params)
        
        # Форматируем данные

        headlines = [
            {
                'id': str(row[0]),
                'title': row[1],
                'link': row[2],
                'content': row[3],
                'source': row[4],
                'category': row[5],
                'parsed_date': row[6].strftime('%Y-%m-%d %H:%M:%S')
            }
            for row in result.result_rows
        ]
        
        # Подсчет общего количества записей для пагинации
        count_query = '''
            SELECT COUNT(*)
            FROM news.ria_headlines
            WHERE parsed_date >= %(start_date)s
        '''
        
        if category:
            count_query += ' AND category = %(category)s'
            
        total_count = client.query(count_query, parameters=params).result_rows[0][0]
        total_pages = (total_count + page_size - 1) // page_size
        
        # Получаем список доступных категорий для фильтрации
        categories_query = 'SELECT DISTINCT category FROM news.ria_headlines ORDER BY category'
        categories = [row[0] for row in client.query(categories_query).result_rows]
        
        return jsonify({
            'status': 'success',
            'data': headlines,
            'total_pages': total_pages,
            'current_page': page,
            'available_categories': categories
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        client.close()


@app.route('/api/categorized', methods=['GET'])
def get_categorized_news():
    """Получение новостей по определенной категории из специализированных таблиц"""
    try:
        page = int(request.args.get('page', 1))
        page_size = 10  # Количество записей на странице
        category = request.args.get('category', 'ukraine')  # Категория по умолчанию - Украина
        source = request.args.get('source', 'all')  # Источник (ria, israil или all)
        days = int(request.args.get('days', 7))
        
        client = get_clickhouse_client()
        
        # Проверяем, что категория допустима
        valid_categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
        if category not in valid_categories:
            return jsonify({'status': 'error', 'message': f'Недопустимая категория. Допустимые категории: {valid_categories}'}), 400
        
        # Формируем запрос в зависимости от источника
        if source == 'ria':
            query = f'''
                SELECT id, title, link, content, source, category, parsed_date
                FROM news.ria_{category}
                WHERE parsed_date >= %(start_date)s
                ORDER BY parsed_date DESC
                LIMIT %(limit)s OFFSET %(offset)s
            '''
            count_query = f'''
                SELECT COUNT(*)
                FROM news.ria_{category}
                WHERE parsed_date >= %(start_date)s
            '''
        elif source == 'israil':
            query = f'''
                SELECT id, title, link, content, source, category, parsed_date
                FROM news.israil_{category}
                WHERE parsed_date >= %(start_date)s
                ORDER BY parsed_date DESC
                LIMIT %(limit)s OFFSET %(offset)s
            '''
            count_query = f'''
                SELECT COUNT(*)
                FROM news.israil_{category}
                WHERE parsed_date >= %(start_date)s
            '''
        else:  # all sources
            query = f'''
                SELECT id, title, link, content, source, category, parsed_date
                FROM
                (
                    SELECT id, title, link, content, source, category, parsed_date
                    FROM news.ria_{category}
                    UNION ALL
                    SELECT id, title, link, content, source, category, parsed_date
                    FROM news.israil_{category}
                )
                WHERE parsed_date >= %(start_date)s
                ORDER BY parsed_date DESC
                LIMIT %(limit)s OFFSET %(offset)s
            '''
            count_query = f'''
                SELECT COUNT(*)
                FROM
                (
                    SELECT id, title, link, content, source, category, parsed_date
                    FROM news.ria_{category}
                    UNION ALL
                    SELECT id, title, link, content, source, category, parsed_date
                    FROM news.israil_{category}
                )
                WHERE parsed_date >= %(start_date)s
            '''
        
        # Параметры запроса
        start_date = datetime.datetime.now() - datetime.timedelta(days=days)
        params = {
            'start_date': start_date,
            'limit': page_size,
            'offset': (page - 1) * page_size
        }
        
        result = client.query(query, parameters=params)
        
        # Форматируем данные
        headlines = [
            {
                'id': str(row[0]),
                'title': row[1],
                'link': row[2],
                'content': row[3],
                'source': row[4],
                'category': row[5],
                'parsed_date': row[6].strftime('%Y-%m-%d %H:%M:%S')
            }
            for row in result.result_rows
        ]
        
        # Подсчет общего количества записей для пагинации
        total_count = client.query(count_query, parameters=params).result_rows[0][0]
        total_pages = (total_count + page_size - 1) // page_size
        
        # Получаем статистику по категориям
        stats = []
        for cat in valid_categories:
            ria_count = client.query(f"SELECT COUNT(*) FROM news.ria_{cat}").result_rows[0][0]
            israil_count = client.query(f"SELECT COUNT(*) FROM news.israil_{cat}").result_rows[0][0]
            stats.append({
                'category': cat,
                'ria_count': ria_count,
                'israil_count': israil_count,
                'total': ria_count + israil_count
            })
        
        return jsonify({
            'status': 'success',
            'data': headlines,
            'total_pages': total_pages,
            'current_page': page,
            'category': category,
            'source': source,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        client.close()

# Маршруты для страниц
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')

@app.route('/analytics')
def serve_analytics():
    return app.send_static_file('analytics.html')

@app.route('/clickhouse')
def serve_clickhouse():
    return app.send_static_file('clickhouse.html')

@app.route('/reports')
def serve_reports():
    return app.send_static_file('reports.html')

@app.route('/trends')
def serve_trends():
    return app.send_static_file('trends.html')

@app.route('/archive')
def serve_archive():
    return app.send_static_file('archive.html')

@app.route('/about')
def serve_about():
    return app.send_static_file('about.html')

@app.route('/forecast')
def forecast():
    return app.send_static_file('forecast.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)