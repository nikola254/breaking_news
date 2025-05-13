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
    try:
        # Параметры запроса: категория и страница
        category = request.args.get('category', 'Украина')
        page = int(request.args.get('page', 1))
        page_size = 5  # Количество записей на странице
        days = int(request.args.get('days', 7))

        client = get_clickhouse_client()
        
        # Определяем, из какой таблицы брать данные в зависимости от категории
        if category in ['Украина', 'Фейки', 'Ближний восток']:
            # Используем таблицу ria_headlines для основных категорий
            table_name = 'news.ria_headlines'
            
            # Базовый запрос
            query = '''
                SELECT id, title, link, content, source, category, parsed_date
                FROM news.ria_headlines
                WHERE category = %(category)s
                AND parsed_date >= %(start_date)s
                ORDER BY parsed_date DESC
                LIMIT %(limit)s OFFSET %(offset)s
            '''
            
            # Параметры запроса
            start_date = datetime.datetime.now() - datetime.timedelta(days=days)
            params = {
                'category': category,
                'start_date': start_date,
                'limit': page_size,
                'offset': (page - 1) * page_size
            }
            
            result = client.query(query, parameters=params)
            
            # Форматируем данные
            news = [
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
                WHERE category = %(category)s
                AND parsed_date >= %(start_date)s
            '''
        else:
            # Для неизвестных категорий возвращаем пустой список
            news = []
            total_count = 0
            total_pages = 0
            return jsonify({
                'status': 'success',
                'data': news,
                'total_pages': total_pages,
                'current_page': page,
                'message': f'Категория {category} не найдена'
            })
        
        total_count = client.query(count_query, parameters=params).result_rows[0][0]
        total_pages = (total_count + page_size - 1) // page_size

        return jsonify({
            'status': 'success',
            'data': news,
            'total_pages': total_pages,
            'current_page': page
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