import os
import requests
from flask import jsonify, request, render_template, current_app
import clickhouse_connect
import datetime
import threading
import subprocess
import random
from app import app
from app.models import get_clickhouse_client

# Маршруты для страниц приложения
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/clickhouse')
def database():
    return render_template('database.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/predict')
def predict():
    return render_template('predict.html')

@app.route('/trends')
def trends():
    return render_template('trends.html')

@app.route('/archive')
def archive():
    return render_template('archive.html')

@app.route('/about')
def about():
    return render_template('about.html')

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
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.lenta_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.rbc_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.gazeta_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.kommersant_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.tsn_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.unian_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.rt_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.cnn_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.aljazeera_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.reuters_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.france24_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.dw_headlines
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.euronews_headlines
                    
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
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.lenta_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.rbc_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.gazeta_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.kommersant_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.tsn_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.unian_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.rt_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.cnn_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.aljazeera_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.reuters_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.france24_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.dw_headlines
                    WHERE category = '{category}'
                    
                    UNION ALL
                    
                    SELECT id, title, link, content, source, category, parsed_date, '' as source_links, '' as message_link, '' as channel
                    FROM news.euronews_headlines
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
            # Обработка конкретных источников
            source_tables = {
                'ria': 'news.ria_headlines',
                'lenta': 'news.lenta_headlines',
                'rbc': 'news.rbc_headlines',
                'gazeta': 'news.gazeta_headlines',
                'kommersant': 'news.kommersant_headlines',
                'tsn': 'news.tsn_headlines',
                'unian': 'news.unian_headlines',
                'rt': 'news.rt_headlines',
                'cnn': 'news.cnn_headlines',
                'aljazeera': 'news.aljazeera_headlines',
                'reuters': 'news.reuters_headlines',
                'france24': 'news.france24_headlines',
                'dw': 'news.dw_headlines',
                'euronews': 'news.euronews_headlines',
                'israil': 'news.israil_headlines',
                'telegram': 'news.telegram_headlines'
            }
            
            if source not in source_tables:
                return jsonify({'status': 'error', 'message': 'Недопустимый источник'}), 400
            
            table_name = source_tables[source]
            
            if category == 'all':
                if source == 'telegram':
                    query = f'''
                        SELECT 
                            id, title, '' as link, content, source, category, parsed_date,
                            '' as israil_link, '' as source_links, message_link as telegram_link, channel as telegram_channel
                        FROM {table_name}
                        ORDER BY parsed_date DESC
                        LIMIT {limit} OFFSET {offset}
                    '''
                elif source == 'israil':
                    query = f'''
                        SELECT 
                            id, title, '' as link, content, source, category, parsed_date,
                            link as israil_link, source_links, '' as telegram_link, '' as telegram_channel
                        FROM {table_name}
                        ORDER BY parsed_date DESC
                        LIMIT {limit} OFFSET {offset}
                    '''
                else:
                    query = f'''
                        SELECT 
                            id, title, link, content, source, category, parsed_date,
                            '' as israil_link, '' as source_links, '' as telegram_link, '' as telegram_channel
                        FROM {table_name}
                        ORDER BY parsed_date DESC
                        LIMIT {limit} OFFSET {offset}
                    '''
            else:
                if source == 'telegram':
                    query = f'''
                        SELECT 
                            id, title, '' as link, content, source, category, parsed_date,
                            '' as israil_link, '' as source_links, message_link as telegram_link, channel as telegram_channel
                        FROM {table_name}
                        WHERE category = '{category}'
                        ORDER BY parsed_date DESC
                        LIMIT {limit} OFFSET {offset}
                    '''
                elif source == 'israil':
                    query = f'''
                        SELECT 
                            id, title, '' as link, content, source, category, parsed_date,
                            link as israil_link, source_links, '' as telegram_link, '' as telegram_channel
                        FROM {table_name}
                        WHERE category = '{category}'
                        ORDER BY parsed_date DESC
                        LIMIT {limit} OFFSET {offset}
                    '''
                else:
                    query = f'''
                        SELECT 
                            id, title, link, content, source, category, parsed_date,
                            '' as israil_link, '' as source_links, '' as telegram_link, '' as telegram_channel
                        FROM {table_name}
                        WHERE category = '{category}'
                        ORDER BY parsed_date DESC
                        LIMIT {limit} OFFSET {offset}
                    '''
            
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
            if row[6]:  # link для обычных источников
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
        import os
        
        # Получаем базовый путь проекта
        basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        
        # Обрабатываем случай, когда источники переданы в виде строки с разделителями
        if isinstance(source, str) and ',' in source:
            sources = source.split(',')
        else:
            sources = [source]
        
        # Определяем, какой парсер запустить в зависимости от источника
        if 'telegram' in sources or 'all' in sources:
            # Запускаем парсер Telegram в отдельном потоке
            def run_telegram_parser():
                parser_path = os.path.join(basedir, 'parser_telegram.py')
                subprocess.run(['python', parser_path])
            
            thread = threading.Thread(target=run_telegram_parser)
            thread.daemon = True
            thread.start()
        
        if 'israil' in sources or 'all' in sources:
            # Запускаем парсер Израиль в отдельном потоке
            def run_israil_parser():
                parser_path = os.path.join(basedir, 'parser_israil.py')
                subprocess.run(['python', parser_path])
            
            thread = threading.Thread(target=run_israil_parser)
            thread.daemon = True
            thread.start()
        
        if 'ria' in sources or 'all' in sources:
            # Запускаем парсер РИА в отдельном потоке
            def run_ria_parser():
                parser_path = os.path.join(basedir, 'parser_ria.py')
                subprocess.run(['python', parser_path])
            
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
                'parsed_date': row[6].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row[6], 'strftime') else row[6]
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
        if 'client' in locals():
            client.close()
            
# API эндпоинт для отправки промта в DeepSeek
@app.route('/api/deepseek', methods=['POST'])
def deepseek_query():
    data = request.json
    prompt = data.get('prompt', '')
    
    api_key = current_app.config.get('DEEPSEEK_API_KEY')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'API ключ не найден'}), 500

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'status': 'success',
                'response': result['choices'][0]['message']['content'].strip(),
                'usage': result.get('usage', {})
            })
        else:
            return jsonify({
                'status': 'api_error',
                'code': response.status_code,
                'message': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'status': 'server_error',
            'message': str(e)
        }), 500
        
@app.route('/api/openrouter', methods=['POST'])
def openrouter_query():
    data = request.json
    prompt = data.get('prompt', '')
    model = data.get('model', 'meta-llama/llama-3.3-8b-instruct:free')
    
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'OPENROUTER_API_KEY не найден'}), 500

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": data.get('temperature', 0.7),
                "max_tokens": data.get('max_tokens', 2048)
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'status': 'success',
                'response': result['choices'][0]['message']['content'].strip(),
                'usage': result.get('usage', {})
            })
        else:
            return jsonify({
                'status': 'api_error',
                'code': response.status_code,
                'message': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'status': 'server_error',
            'message': str(e)
        }), 500
