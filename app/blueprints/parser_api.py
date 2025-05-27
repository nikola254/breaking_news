from flask import Blueprint, jsonify, request
import threading
import subprocess
import os

# Создаем Blueprint для API парсеров
parser_api_bp = Blueprint('parser_api', __name__, url_prefix='/api')

# API-эндпоинт для запуска парсеров
@parser_api_bp.route('/run_parser', methods=['POST'])
def run_parser():
    try:
        data = request.json
        source = data.get('source', 'all')
        
        # Получаем базовый путь проекта
        basedir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        
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