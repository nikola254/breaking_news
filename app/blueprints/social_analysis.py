from flask import Blueprint, request, jsonify, render_template, session, current_app
from datetime import datetime, timedelta
import asyncio
import logging
import json
from typing import List, Dict, Optional
import threading
import time

# Импорты наших модулей
from app.social_media.vk_api import VKAnalyzer
from app.social_media.ok_api import OKAnalyzer
from app.social_media.telegram_api import TelegramAnalyzer
from app.ai.content_classifier import ExtremistContentClassifier

# ClickHouse для хранения данных
import clickhouse_connect
from config import Config
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Создание Blueprint
social_bp = Blueprint('social_analysis', __name__)

# ClickHouse клиент
clickhouse_client = None

def get_clickhouse_client():
    """Получение клиента ClickHouse"""
    global clickhouse_client
    if clickhouse_client is None:
        try:
            clickhouse_client = clickhouse_connect.get_client(
                host=Config.CLICKHOUSE_HOST,
                port=Config.CLICKHOUSE_PORT,
                username=Config.CLICKHOUSE_USER,
                password=Config.CLICKHOUSE_PASSWORD
            )
            # Создание таблиц если их нет
            create_social_analysis_tables()
        except Exception as e:
            logger.error(f"Ошибка подключения к ClickHouse: {e}")
    return clickhouse_client

def create_social_analysis_tables():
    """Создание таблиц для анализа социальных сетей в ClickHouse"""
    client = clickhouse_client
    if not client:
        return
    
    try:
        # Таблица результатов анализа
        client.command("""
            CREATE TABLE IF NOT EXISTS social_analysis_results (
                id UUID DEFAULT generateUUIDv4(),
                platform String,
                account_url String,
                content String,
                classification String,
                confidence Float32,
                keywords Array(String),
                analysis_date DateTime DEFAULT now(),
                metadata String
            ) ENGINE = MergeTree()
            ORDER BY analysis_date
        """)
        
        # Таблица сессий мониторинга
        client.command("""
            CREATE TABLE IF NOT EXISTS monitoring_sessions (
                session_id UUID DEFAULT generateUUIDv4(),
                session_name String,
                platforms Array(String),
                keywords Array(String),
                is_active UInt8,
                check_interval UInt32,
                created_date DateTime DEFAULT now(),
                last_check DateTime
            ) ENGINE = MergeTree()
            ORDER BY created_date
        """)
        
        logger.info("Таблицы ClickHouse для анализа социальных сетей созданы")
    except Exception as e:
        logger.error(f"Ошибка создания таблиц ClickHouse: {e}")

# Маршрут для отображения страницы анализа социальных сетей
@social_bp.route('/social-analysis', methods=['GET'])
def social_analysis():
    """Отображение страницы анализа социальных сетей"""
    return render_template('social_analysis.html')



def save_analysis_result(platform: str, account_url: str, content: str, 
                        classification: str, confidence: float, keywords: list, metadata: str):
    """Сохранение результата анализа в ClickHouse"""
    try:
        client = get_clickhouse_client()
        if client:
            # Подготавливаем данные как список значений в правильном порядке
            data_row = [
                platform,
                account_url,
                content,
                classification,
                confidence,
                json.dumps(keywords) if isinstance(keywords, list) else str(keywords),
                datetime.now(),
                metadata
            ]
            
            logger.info(f"Сохранение данных в ClickHouse для {platform}: {account_url}")
            # Указываем явно колонки для вставки (исключая id)
            client.insert('social_analysis_results', [data_row], 
                         column_names=['platform', 'account_url', 'content', 'classification', 
                                     'confidence', 'keywords', 'analysis_date', 'metadata'])
            logger.info(f"Результат анализа успешно сохранен для {platform}: {account_url}")
    except Exception as e:
        logger.error(f"Ошибка сохранения в ClickHouse: {e}")
        logger.error(f"Тип ошибки: {type(e).__name__}")
        logger.error(f"Детали ошибки: {str(e)}")
        import traceback
        logger.error(f"Трассировка: {traceback.format_exc()}")

# API маршруты для анализа
@social_bp.route('/social-analysis/analyze-account', methods=['POST'])
def analyze_account():
    """Анализ конкретного аккаунта"""
    try:
        platform = request.form.get('platform')
        account_url = request.form.get('account_url')
        posts_limit = int(request.form.get('posts_limit', 50))
        analysis_type = request.form.get('analysis_type', 'full')
        
        results = {
            'platform': platform,
            'account_url': account_url,
            'posts_analyzed': 0,
            'analysis_date': datetime.now().isoformat(),
            'extremist_content_count': 0,
            'suspicious_content_count': 0,
            'normal_content_count': 0,
            'detailed_results': []
        }
        
        # Реальный анализ для Telegram
        if platform == 'telegram':
            # Извлечение username из URL
            if account_url.startswith('https://t.me/'):
                channel_username = '@' + account_url.split('/')[-1]
            elif account_url.startswith('@'):
                channel_username = account_url
            else:
                channel_username = '@' + account_url
            
            # Асинхронная функция для работы с Telegram
            async def get_telegram_data():
                telegram_analyzer = TelegramAnalyzer(
                    api_id=Config.TELEGRAM_API_ID,
                    api_hash=Config.TELEGRAM_API_HASH,
                    phone_number=Config.TELEGRAM_PHONE
                )
                await telegram_analyzer.initialize(password=Config.TELEGRAM_PASSWORD)
                messages = await telegram_analyzer.get_channel_messages(channel_username, limit=posts_limit)
                await telegram_analyzer.close()
                return messages
            
            # Получение сообщений
            messages = asyncio.run(get_telegram_data())
            
            # Анализ контента с помощью AI
            classifier = ExtremistContentClassifier()
            
            for msg in messages:
                if msg.get('text'):
                    classification = classifier.classify_content(msg['text'])
                    
                    # Подсчет по категориям
                    if classification['label'] == 'extremist':
                        results['extremist_content_count'] += 1
                    elif classification['label'] == 'suspicious':
                        results['suspicious_content_count'] += 1
                    else:
                        results['normal_content_count'] += 1
                    
                    # Подготовка metadata для JSON сериализации
                    msg_metadata = msg.copy()
                    if 'date' in msg_metadata and hasattr(msg_metadata['date'], 'isoformat'):
                        msg_metadata['date'] = msg_metadata['date'].isoformat()
                    
                    # Сохранение в ClickHouse
                    save_analysis_result(
                        platform='telegram',
                        account_url=account_url,
                        content=msg['text'],
                        classification=classification['label'],
                        confidence=classification['confidence'],
                        keywords=classification.get('keywords', []),
                        metadata=json.dumps(msg_metadata)
                    )
                    
                    # Преобразуем datetime в строку для JSON сериализации
                    msg_date = msg.get('date')
                    if msg_date and hasattr(msg_date, 'isoformat'):
                        msg_date = msg_date.isoformat()
                    elif msg_date:
                        msg_date = str(msg_date)
                    
                    results['detailed_results'].append({
                        'message_id': msg.get('id'),
                        'content': msg['text'][:200] + '...' if len(msg['text']) > 200 else msg['text'],
                        'highlighted_text': classification.get('highlighted_text', msg['text']),
                        'threat_color': classification.get('threat_color', '#28a745'),
                        'classification': classification['label'],
                        'confidence': classification['confidence'],
                        'keywords': classification.get('keywords', []),
                        'date': msg_date
                    })
            
            results['posts_analyzed'] = len(messages)
            
        else:
            # Заглушка для других платформ
            results.update({
                'posts_analyzed': posts_limit,
                'extremist_content_count': 2,
                'suspicious_content_count': 5,
                'normal_content_count': posts_limit - 7,
                'detailed_results': [
                    {
                        'content': f'Пример анализа для {platform}...',
                        'classification': 'normal',
                        'confidence': 0.85,
                        'date': datetime.now().isoformat()
                    }
                ]
            })
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Ошибка анализа аккаунта: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@social_bp.route('/social-analysis/search-keywords', methods=['POST'])
def search_keywords():
    """Поиск контента по ключевым словам с анализом экстремистского контента"""
    try:
        keywords = request.form.get('keywords', '')
        platforms = request.form.getlist('platforms')
        
        if not keywords.strip():
            return jsonify({
                'success': False,
                'error': 'Необходимо указать ключевые слова для поиска'
            })
        
        # Разбиваем ключевые слова
        keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        
        # Инициализируем классификатор
        classifier = ExtremistContentClassifier()
        
        results = {
            'total_found': 0,
            'keywords': keywords,
            'platforms': platforms,
            'platform_results': {},
            'analysis_summary': {
                'extremist_count': 0,
                'suspicious_count': 0,
                'normal_count': 0
            }
        }
        
        # Поиск в Telegram (если выбран)
        if 'telegram' in platforms:
            try:
                # Асинхронная функция для поиска в Telegram
                async def search_telegram():
                    telegram_analyzer = TelegramAnalyzer(
                        api_id=Config.TELEGRAM_API_ID,
                        api_hash=Config.TELEGRAM_API_HASH,
                        phone_number=Config.TELEGRAM_PHONE
                    )
                    await telegram_analyzer.initialize(password=Config.TELEGRAM_PASSWORD)
                    
                    # Поиск по популярным каналам (можно расширить)
                    search_channels = ['@breakingnews', '@news24', '@politicsnews']
                    found_items = []
                    
                    for channel in search_channels:
                        try:
                            messages = await telegram_analyzer.get_channel_messages(channel, limit=20)
                            for msg in messages:
                                if msg.get('text'):
                                    # Проверяем наличие ключевых слов
                                    text_lower = msg['text'].lower()
                                    if any(keyword.lower() in text_lower for keyword in keyword_list):
                                        # Анализируем контент
                                        classification = classifier.classify_content(msg['text'])
                                        
                                        # Подсчитываем по категориям
                                        if classification['label'] == 'extremist':
                                            results['analysis_summary']['extremist_count'] += 1
                                        elif classification['label'] == 'suspicious':
                                            results['analysis_summary']['suspicious_count'] += 1
                                        else:
                                            results['analysis_summary']['normal_count'] += 1
                                        
                                        # Сохраняем результат
                                        save_analysis_result(
                                            platform='telegram',
                                            account_url=f"https://t.me/{channel}",
                                            content=msg['text'],
                                            classification=classification['label'],
                                            confidence=classification['confidence'],
                                            keywords=classification.get('keywords', []),
                                            metadata=json.dumps({
                                                'search_keywords': keyword_list,
                                                'message_id': msg.get('id'),
                                                'date': msg.get('date').isoformat() if msg.get('date') else None
                                            })
                                        )
                                        
                                        found_items.append({
                                            'content': msg['text'][:200] + '...' if len(msg['text']) > 200 else msg['text'],
                                            'highlighted_text': classification.get('highlighted_text', msg['text'][:200]),
                                            'threat_color': classification.get('threat_color', '#28a745'),
                                            'classification': classification['label'],
                                            'confidence': classification['confidence'],
                                            'channel': channel,
                                            'date': msg.get('date').isoformat() if msg.get('date') else None,
                                            'url': f"https://t.me/{channel}/{msg.get('id', '')}"
                                        })
                        except Exception as e:
                            logger.warning(f"Ошибка поиска в канале {channel}: {e}")
                            continue
                    
                    await telegram_analyzer.close()
                    return found_items
                
                # Выполняем поиск
                telegram_items = asyncio.run(search_telegram())
                results['platform_results']['telegram'] = {
                    'count': len(telegram_items),
                    'items': telegram_items
                }
                results['total_found'] += len(telegram_items)
                
            except Exception as e:
                logger.error(f"Ошибка поиска в Telegram: {e}")
                results['platform_results']['telegram'] = {
                    'count': 0,
                    'items': [],
                    'error': str(e)
                }
        
        # Заглушки для других платформ (VK, OK)
        if 'vk' in platforms:
            results['platform_results']['vk'] = {
                'count': 0,
                'items': [],
                'error': 'VK API не настроен. Требуется токен доступа.'
            }
        
        if 'ok' in platforms:
            results['platform_results']['ok'] = {
                'count': 0,
                'items': [],
                'error': 'OK API не настроен. Требуются ключи приложения.'
            }
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Ошибка поиска по ключевым словам: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@social_bp.route('/social-analysis/start-monitoring', methods=['POST'])
def start_monitoring():
    """Запуск мониторинга социальных сетей с анализом экстремистского контента"""
    try:
        session_name = request.form.get('session_name')
        platform = request.form.get('platform')
        platforms = [platform] if platform else []
        keywords = request.form.get('monitoring_keywords', '')
        interval = int(request.form.get('interval', 60))  # минуты
        
        if not platforms:
            return jsonify({
                'success': False,
                'error': 'Необходимо выбрать платформу'
            })
        
        if not keywords.strip():
            return jsonify({
                'success': False,
                'error': 'Необходимо указать ключевые слова для мониторинга'
            })
        
        # Создаем уникальный ID сессии
        session_id = f"session_{int(time.time())}_{hash(keywords + str(platforms)) % 10000}"
        
        # Разбиваем ключевые слова
        keyword_list = [kw.strip() for kw in keywords.split(',') if kw.strip()]
        
        # Сохраняем информацию о сессии
        session_info = {
            'id': session_id,
            'session_name': session_name,
            'platforms': platforms,
            'keywords': keyword_list,
            'interval': interval,
            'start_time': datetime.now().isoformat(),
            'status': 'active',
            'found_count': 0,
            'extremist_count': 0,
            'suspicious_count': 0,
            'normal_count': 0
        }
        
        # Добавляем в глобальный список активных сессий
        if not hasattr(current_app, 'monitoring_sessions'):
            current_app.monitoring_sessions = {}
        
        current_app.monitoring_sessions[session_id] = session_info
        
        # Запускаем фоновый процесс мониторинга
        def background_monitoring():
            """Фоновая функция мониторинга"""
            classifier = ExtremistContentClassifier()
            
            while session_id in current_app.monitoring_sessions and \
                  current_app.monitoring_sessions[session_id]['status'] == 'active':
                
                try:
                    # Мониторинг Telegram
                    if 'telegram' in platforms:
                        async def monitor_telegram():
                            telegram_analyzer = TelegramAnalyzer(
                                api_id=Config.TELEGRAM_API_ID,
                                api_hash=Config.TELEGRAM_API_HASH,
                                phone_number=Config.TELEGRAM_PHONE
                            )
                            await telegram_analyzer.initialize(password=Config.TELEGRAM_PASSWORD)
                            
                            # Мониторим популярные каналы
                            monitor_channels = ['@breakingnews', '@news24', '@politicsnews']
                            
                            for channel in monitor_channels:
                                try:
                                    # Получаем последние сообщения
                                    messages = await telegram_analyzer.get_channel_messages(channel, limit=5)
                                    
                                    for msg in messages:
                                        if msg.get('text'):
                                            # Проверяем наличие ключевых слов
                                            text_lower = msg['text'].lower()
                                            if any(keyword.lower() in text_lower for keyword in keyword_list):
                                                # Анализируем контент
                                                classification = classifier.classify_content(msg['text'])
                                                
                                                # Обновляем статистику сессии
                                                current_app.monitoring_sessions[session_id]['found_count'] += 1
                                                if classification['label'] == 'extremist':
                                                    current_app.monitoring_sessions[session_id]['extremist_count'] += 1
                                                elif classification['label'] == 'suspicious':
                                                    current_app.monitoring_sessions[session_id]['suspicious_count'] += 1
                                                else:
                                                    current_app.monitoring_sessions[session_id]['normal_count'] += 1
                                                
                                                # Сохраняем результат
                                                save_analysis_result(
                                                    platform='telegram',
                                                    account_url=f"https://t.me/{channel}",
                                                    content=msg['text'],
                                                    classification=classification['label'],
                                                    confidence=classification['confidence'],
                                                    keywords=classification.get('keywords', []),
                                                    metadata=json.dumps({
                                                        'monitoring_session': session_id,
                                                        'monitor_keywords': keyword_list,
                                                        'message_id': msg.get('id'),
                                                        'date': msg.get('date').isoformat() if msg.get('date') else None
                                                    })
                                                )
                                                
                                                # Логируем найденный контент
                                                logger.info(f"Мониторинг {session_id}: найден контент в {channel}, классификация: {classification['label']}")
                                                
                                except Exception as e:
                                    logger.warning(f"Ошибка мониторинга канала {channel}: {e}")
                                    continue
                            
                            await telegram_analyzer.close()
                        
                        # Выполняем мониторинг Telegram
                        try:
                            asyncio.run(monitor_telegram())
                        except Exception as e:
                            logger.error(f"Ошибка мониторинга Telegram в сессии {session_id}: {e}")
                    
                    # Ждем до следующей проверки
                    time.sleep(interval * 60)  # интервал в минутах
                    
                except Exception as e:
                    logger.error(f"Ошибка в фоновом мониторинге {session_id}: {e}")
                    time.sleep(60)  # Ждем минуту перед повтором
            
            # Помечаем сессию как завершенную
            if session_id in current_app.monitoring_sessions:
                current_app.monitoring_sessions[session_id]['status'] = 'stopped'
                current_app.monitoring_sessions[session_id]['end_time'] = datetime.now().isoformat()
        
        # Запускаем мониторинг в отдельном потоке
        monitoring_thread = threading.Thread(target=background_monitoring, daemon=True)
        monitoring_thread.start()
        
        logger.info(f"Запущен мониторинг {session_id} для платформ: {', '.join(platforms)}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f'Мониторинг "{session_name}" запущен для платформ: {", ".join(platforms)}. Интервал: {interval} мин.'
        })
        
    except Exception as e:
        logger.error(f"Ошибка запуска мониторинга: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

@social_bp.route('/social-analysis/active-sessions', methods=['GET'])
def get_active_sessions():
    """Получение списка активных сессий мониторинга"""
    try:
        # Получаем активные сессии из глобального хранилища
        sessions = []
        
        if hasattr(current_app, 'monitoring_sessions'):
            for session_id, session_info in current_app.monitoring_sessions.items():
                # Форматируем время для отображения
                start_time = session_info.get('start_time', '')
                if start_time:
                    try:
                        # Преобразуем ISO формат в читаемый
                        dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        formatted_time = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        formatted_time = start_time
                else:
                    formatted_time = 'Неизвестно'
                
                sessions.append({
                    'id': session_info['id'],
                    'session_name': session_info.get('session_name', f'Сессия {session_id}'),
                    'is_active': session_info.get('status') == 'active',
                    'check_interval': session_info.get('interval', 60),
                    'last_check': formatted_time,
                    'keywords': ', '.join(session_info.get('keywords', [])),
                    'platforms': session_info.get('platforms', []),
                    'found_count': session_info.get('found_count', 0),
                    'extremist_count': session_info.get('extremist_count', 0),
                    'suspicious_count': session_info.get('suspicious_count', 0),
                    'normal_count': session_info.get('normal_count', 0)
                })
        
        # Если нет активных сессий, показываем пример
        if not sessions:
            sessions = [
                {
                    'id': 'example',
                    'session_name': 'Нет активных сессий',
                    'is_active': False,
                    'check_interval': 0,
                    'last_check': 'Никогда',
                    'keywords': 'Запустите мониторинг для отслеживания контента',
                    'platforms': [],
                    'found_count': 0,
                    'extremist_count': 0,
                    'suspicious_count': 0,
                    'normal_count': 0
                }
            ]
        
        # Сортируем по времени запуска (новые сначала)
        sessions.sort(key=lambda x: x['last_check'], reverse=True)
        
        return jsonify({
            'success': True,
            'sessions': sessions
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения активных сессий: {e}")
        return jsonify({
            'success': False,
            'sessions': [],
            'error': str(e)
        })

@social_bp.route('/social-analysis/stop-session/<session_id>', methods=['POST'])
def stop_session(session_id):
    """Остановка сессии мониторинга"""
    try:
        # Проверяем наличие глобального хранилища сессий
        if not hasattr(current_app, 'monitoring_sessions'):
            return jsonify({
                'success': False,
                'error': 'Нет активных сессий мониторинга'
            })
        
        # Проверяем существование сессии
        if session_id not in current_app.monitoring_sessions:
            return jsonify({
                'success': False,
                'error': f'Сессия {session_id} не найдена'
            })
        
        # Получаем информацию о сессии
        session_info = current_app.monitoring_sessions[session_id]
        session_name = session_info.get('session_name', f'Сессия {session_id}')
        
        # Останавливаем сессию
        current_app.monitoring_sessions[session_id]['status'] = 'stopped'
        current_app.monitoring_sessions[session_id]['end_time'] = datetime.now().isoformat()
        
        logger.info(f"Остановлена сессия мониторинга: {session_id} ({session_name})")
        
        return jsonify({
            'success': True,
            'message': f'Сессия "{session_name}" остановлена успешно'
        })
        
    except Exception as e:
        logger.error(f"Ошибка остановки сессии {session_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        })

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальные переменные для хранения анализаторов
vk_analyzer = None
ok_analyzer = None
telegram_analyzer = None
classifier = ExtremistContentClassifier()

# Статус анализа
analysis_status = {
    'is_running': False,
    'progress': 0,
    'current_task': '',
    'results_count': 0,
    'start_time': None,
    'errors': []
}

def initialize_analyzers():
    """Инициализация анализаторов социальных сетей"""
    global vk_analyzer, ok_analyzer, telegram_analyzer
    
    try:
        # Инициализация VK анализатора (нужен токен доступа)
        vk_token = "YOUR_VK_ACCESS_TOKEN"  # Заменить на реальный токен
        if vk_token != "YOUR_VK_ACCESS_TOKEN":
            vk_analyzer = VKAnalyzer(access_token=vk_token)
            logger.info("VK Analyzer initialized")
        
        # Инициализация OK анализатора (нужны ключи приложения)
        ok_app_id = "YOUR_OK_APP_ID"
        ok_app_key = "YOUR_OK_APP_KEY"
        ok_access_token = "YOUR_OK_ACCESS_TOKEN"
        ok_session_secret = "YOUR_OK_SESSION_SECRET"
        
        if ok_app_id != "YOUR_OK_APP_ID":
            ok_analyzer = OKAnalyzer(
                application_id=ok_app_id,
                application_key=ok_app_key,
                access_token=ok_access_token,
                session_secret_key=ok_session_secret
            )
            logger.info("OK Analyzer initialized")
        
        # Telegram анализатор инициализируется асинхронно при необходимости
        logger.info("Analyzers initialization completed")
        
    except Exception as e:
        logger.error(f"Error initializing analyzers: {e}")

@social_bp.route('/config', methods=['POST'])
def configure_apis():
    """Конфигурация API ключей"""
    try:
        data = request.get_json()
        
        # Сохранение конфигурации в сессии (в продакшене использовать безопасное хранение)
        session['api_config'] = {
            'vk_token': data.get('vk_token', ''),
            'ok_app_id': data.get('ok_app_id', ''),
            'ok_app_key': data.get('ok_app_key', ''),
            'ok_access_token': data.get('ok_access_token', ''),
            'ok_session_secret': data.get('ok_session_secret', ''),
            'telegram_api_id': data.get('telegram_api_id', ''),
            'telegram_api_hash': data.get('telegram_api_hash', ''),
            'telegram_phone': data.get('telegram_phone', '')
        }
        
        return jsonify({
            'success': True,
            'message': 'API конфигурация сохранена'
        })
        
    except Exception as e:
        logger.error(f"Error configuring APIs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@social_bp.route('/analyze', methods=['POST'])
def start_analysis():
    """Запуск анализа социальных сетей"""
    global analysis_status
    
    if analysis_status['is_running']:
        return jsonify({
            'success': False,
            'error': 'Анализ уже выполняется'
        }), 400
    
    try:
        data = request.get_json()
        
        # Параметры анализа
        platforms = data.get('platforms', ['vk', 'ok', 'telegram'])
        keywords = data.get('keywords', [])
        time_range = data.get('time_range', 24)  # часы
        analysis_depth = data.get('analysis_depth', 'medium')
        
        # Сброс статуса
        analysis_status = {
            'is_running': True,
            'progress': 0,
            'current_task': 'Инициализация анализа',
            'results_count': 0,
            'start_time': datetime.now(),
            'errors': []
        }
        
        # Запуск анализа в отдельном потоке
        analysis_thread = threading.Thread(
            target=run_analysis,
            args=(platforms, keywords, time_range, analysis_depth)
        )
        analysis_thread.daemon = True
        analysis_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Анализ запущен',
            'analysis_id': int(time.time())
        })
        
    except Exception as e:
        analysis_status['is_running'] = False
        logger.error(f"Error starting analysis: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def run_analysis(platforms: List[str], keywords: List[str], time_range: int, analysis_depth: str):
    """Выполнение анализа в отдельном потоке"""
    global analysis_status, vk_analyzer, ok_analyzer
    
    try:
        all_results = []
        total_platforms = len(platforms)
        
        # Анализ VKontakte
        if 'vk' in platforms and vk_analyzer:
            analysis_status['current_task'] = 'Анализ ВКонтакте'
            analysis_status['progress'] = 10
            
            try:
                vk_results = analyze_vk_content(keywords, time_range, analysis_depth)
                all_results.extend(vk_results)
                analysis_status['results_count'] += len(vk_results)
            except Exception as e:
                analysis_status['errors'].append(f"VK: {str(e)}")
                logger.error(f"VK analysis error: {e}")
        
        analysis_status['progress'] = 40
        
        # Анализ Одноклассников
        if 'ok' in platforms and ok_analyzer:
            analysis_status['current_task'] = 'Анализ Одноклассников'
            
            try:
                ok_results = analyze_ok_content(keywords, time_range, analysis_depth)
                all_results.extend(ok_results)
                analysis_status['results_count'] += len(ok_results)
            except Exception as e:
                analysis_status['errors'].append(f"OK: {str(e)}")
                logger.error(f"OK analysis error: {e}")
        
        analysis_status['progress'] = 70
        
        # Анализ Telegram
        if 'telegram' in platforms:
            analysis_status['current_task'] = 'Анализ Telegram'
            
            try:
                telegram_results = asyncio.run(analyze_telegram_content(keywords, time_range, analysis_depth))
                all_results.extend(telegram_results)
                analysis_status['results_count'] += len(telegram_results)
            except Exception as e:
                analysis_status['errors'].append(f"Telegram: {str(e)}")
                logger.error(f"Telegram analysis error: {e}")
        
        analysis_status['progress'] = 90
        analysis_status['current_task'] = 'Сохранение результатов'
        
        # Сохранение результатов в базу данных
        save_analysis_results(all_results, keywords, platforms)
        
        analysis_status['progress'] = 100
        analysis_status['current_task'] = 'Анализ завершен'
        analysis_status['is_running'] = False
        
        logger.info(f"Analysis completed. Total results: {len(all_results)}")
        
    except Exception as e:
        analysis_status['is_running'] = False
        analysis_status['errors'].append(f"General error: {str(e)}")
        logger.error(f"Analysis error: {e}")

def analyze_vk_content(keywords: List[str], time_range: int, analysis_depth: str) -> List[Dict]:
    """Анализ контента ВКонтакте"""
    results = []
    
    for keyword in keywords:
        # Поиск постов
        start_time = datetime.now() - timedelta(hours=time_range)
        posts = vk_analyzer.search_posts(keyword, count=100, start_time=start_time)
        
        # Анализ контента
        analyzed_posts = vk_analyzer.analyze_content_batch(posts, keywords)
        
        # Дополнительный анализ с помощью ИИ
        for post in analyzed_posts:
            if post['risk_level'] in ['medium', 'high']:
                ai_result = classifier.analyze_text_combined(post['text'])
                post['ai_analysis'] = ai_result
                results.append(post)
    
    return results

def analyze_ok_content(keywords: List[str], time_range: int, analysis_depth: str) -> List[Dict]:
    """Анализ контента Одноклассников"""
    results = []
    
    for keyword in keywords:
        # Поиск групп
        groups = ok_analyzer.search_groups(keyword, count=20)
        
        # Анализ контента групп
        group_ids = [group['id'] for group in groups]
        suspicious_content = ok_analyzer.monitor_groups(group_ids, keywords)
        
        # Дополнительный анализ с помощью ИИ
        for content in suspicious_content:
            if content['risk_level'] in ['medium', 'high']:
                ai_result = classifier.analyze_text_combined(content['text'])
                content['ai_analysis'] = ai_result
                results.append(content)
    
    return results

async def analyze_telegram_content(keywords: List[str], time_range: int, analysis_depth: str) -> List[Dict]:
    """Анализ контента Telegram"""
    results = []
    
    try:
        # Получение конфигурации из сессии
        config = session.get('api_config', {})
        
        if not all([config.get('telegram_api_id'), config.get('telegram_api_hash'), config.get('telegram_phone')]):
            logger.warning("Telegram API not configured")
            return results
        
        # Инициализация Telegram анализатора
        telegram_analyzer = TelegramAnalyzer(
            api_id=int(config['telegram_api_id']),
            api_hash=config['telegram_api_hash'],
            phone_number=config['telegram_phone']
        )
        
        await telegram_analyzer.initialize()
        
        # Поиск каналов
        all_channels = []
        for keyword in keywords:
            channels = await telegram_analyzer.search_channels(keyword, limit=10)
            all_channels.extend(channels)
        
        # Мониторинг каналов
        channel_usernames = [ch['username'] for ch in all_channels if ch.get('username')]
        suspicious_messages = await telegram_analyzer.monitor_channels(channel_usernames, keywords, time_range)
        
        # Дополнительный анализ с помощью ИИ
        for message in suspicious_messages:
            if message['risk_level'] in ['medium', 'high', 'critical']:
                ai_result = classifier.analyze_text_combined(message['text'])
                message['ai_analysis'] = ai_result
                results.append(message)
        
        await telegram_analyzer.close()
        
    except Exception as e:
        logger.error(f"Telegram analysis error: {e}")
    
    return results

def save_analysis_results(results: List[Dict], keywords: List[str], platforms: List[str]):
    """Сохранение результатов анализа в ClickHouse"""
    try:
        client = get_clickhouse_client()
        if not client:
            logger.error("Ошибка подключения к ClickHouse")
            return
        
        # Подготовка данных для вставки
        insert_data = []
        current_time = datetime.now()
        
        for result in results:
            # Подготовка данных для вставки в ClickHouse
            row_data = {
                'platform': result.get('source', 'unknown'),
                'content': result.get('text', '')[:2000],  # Увеличенное ограничение длины
                'classification': result.get('risk_level', 'normal'),
                'confidence': float(result.get('risk_score', 0)),
                'keywords': ', '.join(result.get('found_keywords', [])),
                'source_url': result.get('url', ''),
                'author': result.get('author', ''),
                'post_date': result.get('date', current_time),
                'analysis_date': current_time,
                'metadata': json.dumps({
                    'ai_analysis': result.get('ai_analysis'),
                    'views': result.get('views', 0),
                    'likes': result.get('likes', 0),
                    'reposts': result.get('reposts', 0),
                    'comments': result.get('comments', 0),
                    'keywords_searched': keywords,
                    'platforms_analyzed': platforms
                })
            }
            insert_data.append(row_data)
        
        if insert_data:
            # Выполнение INSERT запроса
            insert_query = """
                INSERT INTO social_analysis_results (
                    platform, content, classification, confidence, keywords,
                    source_url, author, post_date, analysis_date, metadata
                ) VALUES
            """
            
            # Подготовка значений для вставки
            values = []
            for data in insert_data:
                # Экранирование строк для SQL
                platform = data['platform'].replace("'", "''")
                content = data['content'].replace("'", "''")
                classification = data['classification'].replace("'", "''")
                keywords = data['keywords'].replace("'", "''")
                source_url = data['source_url'].replace("'", "''")
                author = data['author'].replace("'", "''")
                metadata = data['metadata'].replace("'", "''")
                
                post_date_str = data['post_date'].strftime('%Y-%m-%d %H:%M:%S') if isinstance(data['post_date'], datetime) else str(data['post_date'])
                analysis_date_str = data['analysis_date'].strftime('%Y-%m-%d %H:%M:%S')
                
                value = f"('{platform}', '{content}', '{classification}', {data['confidence']}, '{keywords}', '{source_url}', '{author}', '{post_date_str}', '{analysis_date_str}', '{metadata}')"
                values.append(value)
            
            full_query = insert_query + ", ".join(values)
            
            # Выполнение запроса
            client.command(full_query)
            logger.info(f"Saved {len(insert_data)} analysis results to ClickHouse")
        
    except Exception as e:
        logger.error(f"Error saving results to ClickHouse: {e}")
        logger.error(f"Error details: {str(e)}")

@social_bp.route('/status', methods=['GET'])
def get_analysis_status():
    """Получение статуса анализа"""
    global analysis_status
    
    # Добавление времени выполнения
    if analysis_status['start_time']:
        elapsed_time = (datetime.now() - analysis_status['start_time']).total_seconds()
        analysis_status['elapsed_time'] = elapsed_time
    
    return jsonify(analysis_status)

@social_bp.route('/results', methods=['GET'])
def get_analysis_results():
    """Получение результатов анализа из ClickHouse"""
    try:
        client = get_clickhouse_client()
        if not client:
            return jsonify({
                'success': False,
                'error': 'Ошибка подключения к базе данных'
            }), 500
        
        # Параметры запроса
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        platform = request.args.get('platform')
        classification = request.args.get('classification')
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        keywords = request.args.get('keywords')
        
        # Построение WHERE условий
        where_conditions = []
        
        if platform:
            where_conditions.append(f"platform = '{platform}'")
        
        if classification:
            where_conditions.append(f"classification = '{classification}'")
        
        if date_from:
            where_conditions.append(f"analysis_date >= '{date_from}'")
        
        if date_to:
            where_conditions.append(f"analysis_date <= '{date_to}'")
        
        if keywords:
            # Поиск по ключевым словам в массиве keywords или в тексте content
            keyword_condition = f"(hasAny(keywords, ['{keywords}']) OR position(lower(content), lower('{keywords}')) > 0)"
            where_conditions.append(keyword_condition)
        
        # Формирование WHERE части запроса
        where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
        
        # Запрос для получения общего количества записей
        count_query = f"""
            SELECT COUNT(*) as total
            FROM social_analysis_results
            WHERE {where_clause}
        """
        
        total_result = client.query(count_query)
        total_count = total_result.result_rows[0][0] if total_result.result_rows else 0
        
        # Вычисление OFFSET для пагинации
        offset = (page - 1) * per_page
        
        # Основной запрос с пагинацией
        main_query = f"""
            SELECT 
                toString(id) as id,
                platform,
                account_url,
                content,
                classification,
                confidence,
                keywords,
                analysis_date,
                metadata
            FROM social_analysis_results
            WHERE {where_clause}
            ORDER BY analysis_date DESC
            LIMIT {per_page} OFFSET {offset}
        """
        
        result = client.query(main_query)
        
        # Формирование результатов
        results = []
        for row in result.result_rows:
            results.append({
                'id': row[0],
                'platform': row[1],
                'account_url': row[2],
                'content': row[3][:500] + '...' if len(row[3]) > 500 else row[3],  # Ограничиваем длину контента
                'classification': row[4],
                'confidence': float(row[5]),
                'keywords': row[6],
                'analysis_date': row[7].isoformat() if row[7] else None,
                'metadata': row[8]
            })
        
        # Вычисление информации о пагинации
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        return jsonify({
            'success': True,
            'results': results,
            'pagination': {
                'page': page,
                'pages': total_pages,
                'per_page': per_page,
                'total': total_count,
                'has_next': has_next,
                'has_prev': has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting analysis results: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@social_bp.route('/statistics', methods=['GET'])
def get_analysis_statistics():
    """Получение статистики анализа из ClickHouse"""
    try:
        client = get_clickhouse_client()
        if not client:
            return jsonify({
                'success': False,
                'error': 'Ошибка подключения к базе данных'
            }), 500
        
        # Общая статистика
        total_query = "SELECT COUNT(*) as total FROM social_analysis_results"
        total_result = client.query(total_query)
        total_results = total_result.result_rows[0][0] if total_result.result_rows else 0
        
        # Статистика по классификации (уровням риска)
        classification_query = """
            SELECT classification, COUNT(*) as count
            FROM social_analysis_results
            GROUP BY classification
        """
        classification_result = client.query(classification_query)
        classification_stats = {row[0]: row[1] for row in classification_result.result_rows}
        
        # Статистика по платформам
        platform_query = """
            SELECT platform, COUNT(*) as count
            FROM social_analysis_results
            GROUP BY platform
        """
        platform_result = client.query(platform_query)
        platform_stats = {row[0]: row[1] for row in platform_result.result_rows}
        
        # Статистика за последние 24 часа
        last_24h = datetime.now() - timedelta(hours=24)
        recent_query = f"""
            SELECT COUNT(*) as count
            FROM social_analysis_results
            WHERE analysis_date >= '{last_24h.strftime('%Y-%m-%d %H:%M:%S')}'
        """
        recent_result = client.query(recent_query)
        recent_results = recent_result.result_rows[0][0] if recent_result.result_rows else 0
        
        # Статистика экстремистского и подозрительного контента
        high_risk_query = """
            SELECT COUNT(*) as count
            FROM social_analysis_results
            WHERE classification IN ('extremist', 'suspicious')
        """
        high_risk_result = client.query(high_risk_query)
        high_risk_count = high_risk_result.result_rows[0][0] if high_risk_result.result_rows else 0
        
        # Статистика по дням за последнюю неделю
        week_ago = datetime.now() - timedelta(days=7)
        daily_query = f"""
            SELECT 
                toDate(analysis_date) as date,
                COUNT(*) as count
            FROM social_analysis_results
            WHERE analysis_date >= '{week_ago.strftime('%Y-%m-%d')}'
            GROUP BY toDate(analysis_date)
            ORDER BY date
        """
        daily_result = client.query(daily_query)
        daily_stats = {row[0].strftime('%Y-%m-%d'): row[1] for row in daily_result.result_rows}
        
        # Средний уровень уверенности
        confidence_query = "SELECT AVG(confidence) as avg_confidence FROM social_analysis_results"
        confidence_result = client.query(confidence_query)
        avg_confidence = float(confidence_result.result_rows[0][0]) if confidence_result.result_rows and confidence_result.result_rows[0][0] else 0
        
        return jsonify({
            'success': True,
            'statistics': {
                'total_results': total_results,
                'recent_results_24h': recent_results,
                'high_risk_count': high_risk_count,
                'classification_distribution': classification_stats,
                'platform_distribution': platform_stats,
                'daily_stats_week': daily_stats,
                'average_confidence': round(avg_confidence, 2)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@social_bp.route('/export', methods=['GET', 'POST'])
def export_results():
    """Экспорт результатов анализа из ClickHouse"""
    try:
        client = get_clickhouse_client()
        if not client:
            return jsonify({
                'success': False,
                'error': 'Ошибка подключения к базе данных'
            }), 500
        
        # Получение параметров из GET или POST запроса
        if request.method == 'POST':
            data = request.get_json() or {}
            export_format = data.get('format', 'json')
            filters = data.get('filters', {})
        else:
            export_format = request.args.get('format', 'json')
            filters = {
                'classification': request.args.get('classification'),
                'platform': request.args.get('platform'),
                'keywords': request.args.get('keywords'),
                'date_from': request.args.get('date_from'),
                'date_to': request.args.get('date_to')
            }
        
        # Построение SQL запроса
        base_query = """
            SELECT 
                id,
                platform,
                content,
                classification,
                confidence,
                analysis_date,
                keywords,
                source_url,
                author,
                post_date
            FROM social_analysis_results
        """
        
        conditions = []
        
        if filters.get('classification'):
            conditions.append(f"classification = '{filters['classification']}'")
        
        if filters.get('platform'):
            conditions.append(f"platform = '{filters['platform']}'")
        
        if filters.get('keywords'):
            conditions.append(f"positionCaseInsensitive(keywords, '{filters['keywords']}') > 0")
        
        if filters.get('date_from'):
            date_from = filters['date_from']
            if 'T' not in date_from:  # Если только дата без времени
                date_from += ' 00:00:00'
            conditions.append(f"analysis_date >= '{date_from}'")
        
        if filters.get('date_to'):
            date_to = filters['date_to']
            if 'T' not in date_to:  # Если только дата без времени
                date_to += ' 23:59:59'
            conditions.append(f"analysis_date <= '{date_to}'")
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        base_query += " ORDER BY analysis_date DESC LIMIT 10000"  # Ограничение для безопасности
        
        # Выполнение запроса
        result = client.query(base_query)
        
        # Формирование данных для экспорта
        export_data = []
        for row in result.result_rows:
            export_data.append({
                'id': row[0],
                'platform': row[1],
                'content': row[2],
                'classification': row[3],
                'confidence': float(row[4]) if row[4] else 0,
                'analysis_date': row[5].isoformat() if row[5] else '',
                'keywords': row[6],
                'source_url': row[7],
                'author': row[8],
                'post_date': row[9].isoformat() if row[9] else ''
            })
        
        if export_format == 'json':
            return jsonify({
                'success': True,
                'data': export_data,
                'count': len(export_data),
                'format': export_format,
                'exported_at': datetime.now().isoformat()
            })
        
        elif export_format == 'csv':
            import csv
            import io
            from flask import make_response
            
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=[
                'id', 'platform', 'content', 'classification', 'confidence',
                'analysis_date', 'keywords', 'source_url', 'author', 'post_date'
            ])
            writer.writeheader()
            writer.writerows(export_data)
            
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv; charset=utf-8'
            response.headers['Content-Disposition'] = 'attachment; filename=social_analysis_export.csv'
            return response
        
        elif export_format == 'xlsx':
            try:
                import pandas as pd
                import io
                from flask import make_response
                
                df = pd.DataFrame(export_data)
                output = io.BytesIO()
                
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Social Analysis Export', index=False)
                
                output.seek(0)
                response = make_response(output.getvalue())
                response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                response.headers['Content-Disposition'] = 'attachment; filename=social_analysis_export.xlsx'
                return response
            except ImportError:
                return jsonify({
                    'success': False,
                    'error': 'Для экспорта в XLSX требуется установка pandas и openpyxl'
                }), 500
        
        else:
            return jsonify({
                'success': False,
                'error': 'Неподдерживаемый формат экспорта. Доступные форматы: json, csv, xlsx'
            }), 400
        
    except Exception as e:
        logger.error(f"Error exporting results: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Инициализация анализаторов при загрузке модуля
initialize_analyzers()