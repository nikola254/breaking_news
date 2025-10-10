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

@app.route('/favicon.ico')
def favicon():
    """Обработчик для favicon.ico - предотвращает ошибки 404 в логах"""
    return '', 204  # Возвращаем пустой ответ с кодом 204 No Content

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

@app.route('/parser-status')
def parser_status():
    return render_template('parser_status.html')

# API-эндпоинт для получения новостей
# Функция get_news удалена - используется версия из blueprint news_api.py

# API-эндпоинты для мониторинга парсеров
@app.route('/api/parser-status')
def api_parser_status():
    """API для получения статуса всех парсеров"""
    try:
        from parsers.parser_manager import ParserManager
        
        manager = ParserManager()
        
        # Получаем статистику парсеров
        parsers_data = []
        for parser_key, parser_info in manager.parsers.items():
            parser_data = {
                'name': parser_info['name'],
                'status': 'idle',  # По умолчанию
                'articles_processed': 0,
                'articles_saved': 0,
                'validation_rejected': 0,
                'last_run': None,
                'errors': []
            }
            
            # Здесь можно добавить логику получения реального статуса
            # из базы данных или файлов логов
            parsers_data.append(parser_data)
        
        # Общая статистика
        overall_stats = {
            'total_parsers': len(parsers_data),
            'active_parsers': sum(1 for p in parsers_data if p['status'] == 'running'),
            'total_articles': sum(p['articles_processed'] for p in parsers_data),
            'avg_tension': 50.0,  # Заглушка
            'avg_spike': 30.0,    # Заглушка
            'validation_rejected': sum(p['validation_rejected'] for p in parsers_data)
        }
        
        # Распределение по категориям (заглушка)
        category_distribution = {
            'Военные операции': 15,
            'Гуманитарный кризис': 8,
            'Экономические последствия': 12,
            'Политические решения': 10,
            'Информационно-социальные аспекты': 5
        }
        
        # Статистика напряженности (заглушка)
        tension_stats = {
            'avg_social_tension': 65.5,
            'avg_spike': 42.3
        }
        
        return jsonify({
            'success': True,
            'parsers': parsers_data,
            'overall_stats': overall_stats,
            'category_distribution': category_distribution,
            'tension_stats': tension_stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/parser-start-all', methods=['POST'])
def api_parser_start_all():
    """API для запуска всех парсеров"""
    try:
        from parsers.parser_manager import ParserManager
        
        manager = ParserManager()
        
        # Запускаем все парсеры в отдельном потоке
        def run_parsers():
            try:
                result = manager.run_all_parsers_with_callback(max_workers=4)
                print(f"Парсинг завершен: {result['successful']} успешно, {result['failed']} с ошибками")
            except Exception as e:
                print(f"Ошибка при запуске парсеров: {e}")
        
        thread = threading.Thread(target=run_parsers)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Парсеры запущены в фоновом режиме',
            'started': len(manager.parsers)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/parser-stop-all', methods=['POST'])
def api_parser_stop_all():
    """API для остановки всех парсеров"""
    try:
        # Здесь должна быть логика остановки парсеров
        # Пока что просто возвращаем успех
        return jsonify({
            'success': True,
            'message': 'Все парсеры остановлены'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
            SELECT id, title, content, channel, message_id, message_link, published_date
            FROM news.telegram_headlines
            WHERE published_date >= %(start_date)s
        '''
        
        # Добавляем фильтр по каналу, если указан
        if channel:
            query += ' AND channel = %(channel)s'
            
        query += '''
            ORDER BY published_date DESC
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
                'published_date': row[6].strftime('%Y-%m-%d %H:%M:%S') if hasattr(row[6], 'strftime') else row[6]
            }
            for row in result.result_rows
        ]
        
        # Подсчет общего количества записей для пагинации
        count_query = '''
            SELECT COUNT(*)
            FROM news.telegram_headlines
            WHERE published_date >= %(start_date)s
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
