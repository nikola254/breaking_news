"""API для управления парсерами новостей.

Этот модуль содержит функции для:
- Запуска парсеров новостей из различных источников
- Мониторинга процесса парсинга через WebSocket
- Управления активными процессами парсинга
- Real-time логирования процесса парсинга
"""

from flask import Blueprint, request, jsonify
from flask_socketio import SocketIO, emit
import threading
import subprocess
import os
import sys
from io import StringIO
import time

# Создаем Blueprint для API парсеров
parser_api_bp = Blueprint('parser_api', __name__, url_prefix='/api')

# Глобальная переменная для SocketIO (будет инициализирована в main app)
socketio = None

# Глобальный словарь для отслеживания активных процессов парсинга
active_parsers = {}

def init_socketio(app_socketio):
    """Инициализация SocketIO для использования в parser_api.
    
    Args:
        app_socketio: Экземпляр SocketIO из основного приложения
    """
    global socketio
    socketio = app_socketio

def run_parser_with_logging(parser_path, source_name):
    """Запускает парсер и передает его вывод через WebSocket.
    
    Функция выполняет парсер в отдельном процессе и передает
    все сообщения о ходе выполнения через WebSocket соединение
    для real-time мониторинга.
    
    Args:
        parser_path (str): Путь к файлу парсера
        source_name (str): Название источника для логирования
    """
    try:
        # Отправляем начальное сообщение
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Запуск парсера {source_name}...',
                'type': 'info',
                'source': source_name
            })
        
        # Проверяем существование файла парсера
        if not os.path.exists(parser_path):
            if socketio:
                socketio.emit('parser_log', {
                    'message': f'Ошибка: файл парсера {parser_path} не найден',
                    'type': 'error',
                    'source': source_name
                })
            return
        
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Файл парсера найден: {parser_path}',
                'type': 'info',
                'source': source_name
            })
        
        # Запускаем процесс парсера
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Создание процесса для {source_name}...',
                'type': 'info',
                'source': source_name
            })
        
        process = subprocess.Popen(
            ['python', parser_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Сохраняем процесс в глобальном словаре
        active_parsers[source_name] = process
        
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Процесс {source_name} создан с PID: {process.pid}',
                'type': 'info',
                'source': source_name
            })
        
        # Читаем вывод построчно и отправляем через WebSocket
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Начинаем чтение вывода процесса {source_name}...',
                'type': 'info',
                'source': source_name
            })
        
        line_count = 0
        for line in iter(process.stdout.readline, ''):
            line_count += 1
            if line.strip():
                # Определяем тип сообщения на основе содержимого
                message_type = 'info'
                if 'Ошибка' in line or 'Error' in line:
                    message_type = 'error'
                elif 'Найдена новая статья' in line or 'Добавлено' in line or 'Получено' in line:
                    message_type = 'success'
                
                if socketio:
                    socketio.emit('parser_log', {
                        'message': line.strip(),
                        'type': message_type,
                        'source': source_name
                    })
            
            # Логируем каждые 10 строк для отладки
            if line_count % 10 == 0 and socketio:
                socketio.emit('parser_log', {
                    'message': f'Обработано {line_count} строк вывода от {source_name}',
                    'type': 'debug',
                    'source': source_name
                })
        
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Завершено чтение вывода {source_name}. Всего строк: {line_count}',
                'type': 'info',
                'source': source_name
            })
        
        # Ждем завершения процесса
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Ожидание завершения процесса {source_name}...',
                'type': 'info',
                'source': source_name
            })
        
        process.wait()
        
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Процесс {source_name} завершился с кодом: {process.returncode}',
                'type': 'info',
                'source': source_name
            })
        
        # Удаляем процесс из словаря активных процессов
        if source_name in active_parsers:
            del active_parsers[source_name]
        
        # Отправляем финальное сообщение
        if socketio:
            if process.returncode == 0:
                socketio.emit('parser_log', {
                    'message': f'Парсер {source_name} завершен успешно',
                    'type': 'success',
                    'source': source_name
                })
            else:
                socketio.emit('parser_log', {
                    'message': f'Парсер {source_name} завершен с ошибкой (код: {process.returncode})',
                    'type': 'error',
                    'source': source_name
                })
                
    except Exception as e:
        # Удаляем процесс из словаря в случае ошибки
        if source_name in active_parsers:
            del active_parsers[source_name]
            
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Исключение при запуске парсера {source_name}: {str(e)}',
                'type': 'error',
                'source': source_name
            })
            socketio.emit('parser_log', {
                'message': f'Тип исключения: {type(e).__name__}',
                'type': 'error',
                'source': source_name
            })

def run_universal_parser_with_logging(parser_path, site_url):
    """Запускает универсальный парсер с указанным URL и передает его вывод через WebSocket.
    
    Args:
        parser_path (str): Путь к файлу универсального парсера
        site_url (str): URL сайта для парсинга
    """
    try:
        source_name = f"universal_{site_url}"
        
        # Отправляем начальное сообщение
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Запуск универсального парсера для {site_url}...',
                'type': 'info',
                'source': source_name
            })
        
        # Проверяем существование файла парсера
        if not os.path.exists(parser_path):
            if socketio:
                socketio.emit('parser_log', {
                    'message': f'Ошибка: файл универсального парсера {parser_path} не найден',
                    'type': 'error',
                    'source': source_name
                })
            return
        
        # Запускаем процесс универсального парсера с URL в качестве аргумента
        process = subprocess.Popen(
            ['python', parser_path, '--url', site_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Сохраняем процесс в глобальном словаре
        active_parsers[source_name] = process
        
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Универсальный парсер для {site_url} создан с PID: {process.pid}',
                'type': 'info',
                'source': source_name
            })
        
        # Читаем вывод построчно и отправляем через WebSocket
        line_count = 0
        for line in iter(process.stdout.readline, ''):
            line_count += 1
            if line.strip():
                # Определяем тип сообщения на основе содержимого
                message_type = 'info'
                if 'Ошибка' in line or 'Error' in line:
                    message_type = 'error'
                elif 'Найдена новая статья' in line or 'Добавлено' in line or 'Получено' in line:
                    message_type = 'success'
                
                if socketio:
                    socketio.emit('parser_log', {
                        'message': line.strip(),
                        'type': message_type,
                        'source': source_name
                    })
        
        # Ждем завершения процесса
        process.wait()
        
        # Удаляем процесс из словаря активных процессов
        if source_name in active_parsers:
            del active_parsers[source_name]
        
        # Отправляем финальное сообщение
        if socketio:
            if process.returncode == 0:
                socketio.emit('parser_log', {
                    'message': f'Универсальный парсер для {site_url} завершен успешно',
                    'type': 'success',
                    'source': source_name
                })
            else:
                socketio.emit('parser_log', {
                    'message': f'Универсальный парсер для {site_url} завершен с ошибкой (код: {process.returncode})',
                    'type': 'error',
                    'source': source_name
                })
                
    except Exception as e:
        # Удаляем процесс из словаря в случае ошибки
        if source_name in active_parsers:
            del active_parsers[source_name]
            
        if socketio:
            socketio.emit('parser_log', {
                'message': f'Исключение при запуске универсального парсера для {site_url}: {str(e)}',
                'type': 'error',
                'source': source_name
            })

# API-эндпоинт для запуска парсеров
@parser_api_bp.route('/run_parser', methods=['POST'])
def run_parser():
    """Запуск парсеров новостей из указанных источников.
    
    Принимает JSON с массивом источников и запускает соответствующие
    парсеры в отдельных потоках. Поддерживает real-time мониторинг
    через WebSocket.
    
    Request JSON:
        sources (list): Список источников для парсинга ['telegram', 'ria', 'israil']
        source (str): Альтернативный формат - строка с источниками через запятую
    
    Returns:
        JSON: Статус запуска парсеров
    """
    try:
        data = request.json
        sources = data.get('sources', [])
        
        # Получаем базовый путь проекта
        basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
        # Обрабатываем случай совместимости со старым форматом
        if not sources:
            source = data.get('source', 'all')
            if isinstance(source, str) and ',' in source:
                sources = source.split(',')
            else:
                sources = [source]
        
        # Словарь всех доступных парсеров
        available_parsers = {
            'ria': 'parser_ria.py',
            'lenta': 'parser_lenta.py',
            'rbc': 'parser_rbc.py',
            'gazeta': 'parser_gazeta.py',
            'kommersant': 'parser_kommersant.py',
            'tsn': 'parser_tsn.py',
            'unian': 'parser_unian.py',
            'rt': 'parser_rt.py',
            'cnn': 'parser_cnn.py',
            'aljazeera': 'parser_aljazeera.py',
            'reuters': 'parser_reuters.py',
            'france24': 'parser_france24.py',
            'dw': 'parser_dw.py',
            'euronews': 'parser_euronews.py',
            'israil': 'parser_israil.py',
            'telegram': 'parser_telegram.py',
            'twitter': 'parser_twitter.py',
            'vk': 'parser_vk.py',
            'ok': 'parser_ok.py'
        }
        
        # Определяем, какие парсеры запустить
        parsers_to_run = []
        universal_sites = []
        
        if 'all' in sources:
            parsers_to_run = list(available_parsers.keys())
        else:
            for source in sources:
                if isinstance(source, dict) and source.get('type') == 'universal':
                    universal_sites.append(source)
                elif source in available_parsers:
                    parsers_to_run.append(source)
        
        # Запускаем стандартные парсеры в отдельных потоках
        for parser_name in parsers_to_run:
            parser_file = available_parsers[parser_name]
            
            def run_specific_parser(name, file):
                parser_path = os.path.join(basedir, 'parsers', file)
                run_parser_with_logging(parser_path, name)
            
            thread = threading.Thread(target=run_specific_parser, args=(parser_name, parser_file))
            thread.daemon = True
            thread.start()
        
        # Запускаем универсальные парсеры для пользовательских сайтов
        for site_config in universal_sites:
            site_url = site_config.get('url')
            
            def run_universal_parser_with_category_creation(url):
                # Сначала создаем таблицу для нового сайта
                try:
                    # Импортируем функцию создания таблицы
                    sys.path.append(os.path.join(basedir, 'parsers'))
                    from news_categories import create_custom_table_for_site
                    
                    # Создаем таблицу для пользовательского сайта
                    table_name = create_custom_table_for_site(url)
                    
                    if socketio:
                        socketio.emit('parser_log', {
                            'message': f'Создана таблица {table_name} для сайта {url}',
                            'type': 'success',
                            'source': 'universal'
                        })
                except Exception as e:
                    if socketio:
                        socketio.emit('parser_log', {
                            'message': f'Ошибка при создании таблицы для {url}: {str(e)}',
                            'type': 'error',
                            'source': 'universal'
                        })
                
                # Затем запускаем парсер
                parser_path = os.path.join(basedir, 'parsers', 'universal_parser.py')
                run_universal_parser_with_logging(parser_path, url)
            
            thread = threading.Thread(target=run_universal_parser_with_category_creation, args=(site_url,))
            thread.daemon = True
            thread.start()
        

        return jsonify({
            'status': 'success',
            'message': f'Парсеры для источников {sources} успешно запущены'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@parser_api_bp.route('/stop_parser', methods=['POST'])
def stop_parser():
    """Остановка активных парсеров.
    
    Принимает JSON с массивом источников и останавливает
    соответствующие активные процессы парсинга.
    
    Request JSON:
        sources (list): Список источников для остановки ['telegram', 'ria', 'israil']
        source (str): Альтернативный формат - строка с источниками через запятую
    
    Returns:
        JSON: Статус остановки парсеров
    """
    try:
        data = request.json
        sources = data.get('sources', [])
        
        # Обрабатываем случай совместимости со старым форматом
        if not sources:
            source = data.get('source', 'all')
            if isinstance(source, str) and ',' in source:
                sources = source.split(',')
            else:
                sources = [source]
        
        stopped_parsers = []
        
        for source in sources:
            if source == 'all':
                # Останавливаем все активные парсеры
                for parser_name, process in list(active_parsers.items()):
                    try:
                        process.terminate()
                        stopped_parsers.append(parser_name)
                        if socketio:
                            socketio.emit('parser_log', {
                                'message': f'Парсер {parser_name} остановлен пользователем',
                                'type': 'info',
                                'source': parser_name
                            })
                    except Exception as e:
                        if socketio:
                            socketio.emit('parser_log', {
                                'message': f'Ошибка при остановке парсера {parser_name}: {str(e)}',
                                'type': 'error',
                                'source': parser_name
                            })
                active_parsers.clear()
                break
            elif source in active_parsers:
                # Останавливаем конкретный парсер
                try:
                    process = active_parsers[source]
                    process.terminate()
                    del active_parsers[source]
                    stopped_parsers.append(source)
                    if socketio:
                        socketio.emit('parser_log', {
                            'message': f'Парсер {source} остановлен пользователем',
                            'type': 'info',
                            'source': source
                        })
                except Exception as e:
                    if socketio:
                        socketio.emit('parser_log', {
                            'message': f'Ошибка при остановке парсера {source}: {str(e)}',
                            'type': 'error',
                            'source': source
                        })
        
        if stopped_parsers:
            return jsonify({
                'status': 'success',
                'message': f'Остановлены парсеры: {stopped_parsers}'
            })
        else:
            return jsonify({
                'status': 'info',
                'message': 'Нет активных парсеров для остановки'
            })
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# API-эндпоинт для получения статуса активных парсеров
@parser_api_bp.route('/parser_status', methods=['GET'])
def parser_status():
    """Получение статуса активных парсеров.
    
    Returns:
        JSON: Список активных парсеров
    """
    try:
        return jsonify({
            'status': 'success',
            'active_parsers': list(active_parsers.keys())
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500