#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import threading
import time
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

class CallbackHandler(BaseHTTPRequestHandler):
    """Обработчик callback'ов от gen-api.ru"""
    
    def __init__(self, callback_storage, *args, **kwargs):
        self.callback_storage = callback_storage
        super().__init__(*args, **kwargs)
    
    def do_POST(self):
        """Обрабатывает POST запросы от API"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Парсим JSON данные
            callback_data = json.loads(post_data.decode('utf-8'))
            
            request_id = callback_data.get('request_id')
            status = callback_data.get('status')
            
            logger.info(f"Получен callback для request_id {request_id}, статус: {status}")
            
            if status == 'success':
                # Сохраняем результат
                self.callback_storage[request_id] = {
                    'status': 'completed',
                    'result': callback_data.get('output', ''),
                    'timestamp': time.time()
                }
                logger.info(f"Результат сохранен для request_id {request_id}")
            elif status == 'failed':
                # Сохраняем ошибку
                self.callback_storage[request_id] = {
                    'status': 'failed',
                    'error': callback_data.get('error', 'Unknown error'),
                    'timestamp': time.time()
                }
                logger.error(f"Ошибка для request_id {request_id}: {callback_data.get('error', 'Unknown error')}")
            
            # Отправляем ответ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'received'}).encode())
            
        except Exception as e:
            logger.error(f"Ошибка при обработке callback: {e}")
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Отключаем стандартное логирование HTTP сервера"""
        pass

class CallbackServer:
    """HTTP сервер для получения callback'ов от gen-api.ru"""
    
    def __init__(self, port=8081):
        self.port = port
        self.callback_storage = {}
        self.server = None
        self.server_thread = None
        self.public_url = None
        
    def start(self):
        """Запускает сервер в отдельном потоке"""
        try:
            handler = lambda *args, **kwargs: CallbackHandler(self.callback_storage, *args, **kwargs)
            self.server = HTTPServer(('localhost', self.port), handler)
            
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            logger.info(f"Callback сервер запущен на порту {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при запуске callback сервера: {e}")
            return False
    
    def stop(self):
        """Останавливает сервер"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            logger.info("Callback сервер остановлен")
    
    def get_callback_url(self):
        """Возвращает URL для callback'ов"""
        if self.public_url:
            return f"{self.public_url}/callback"
        return f"http://localhost:{self.port}/callback"
    
    def get_ngrok_url(self):
        """Получает публичный URL от ngrok API"""
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get('tunnels', [])
                for tunnel in tunnels:
                    if tunnel.get('proto') == 'https' and tunnel.get('config', {}).get('addr') == f'localhost:{self.port}':
                        self.public_url = tunnel.get('public_url')
                        logger.info(f"Найден ngrok URL: {self.public_url}")
                        return self.public_url
                logger.warning("Ngrok туннель не найден")
            else:
                logger.warning(f"Не удалось получить ngrok URL: {response.status_code}")
        except Exception as e:
            logger.warning(f"Ошибка при получении ngrok URL: {e}")
        return None
    
    def check_ngrok_status(self):
        """Проверяет статус ngrok и обновляет публичный URL"""
        if not self.public_url:
            self.get_ngrok_url()
        return self.public_url is not None
    
    def wait_for_result(self, request_id, timeout=60):
        """Ждет результат для указанного request_id"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if request_id in self.callback_storage:
                result = self.callback_storage[request_id]
                if result['status'] == 'completed':
                    return result['result']
                elif result['status'] == 'failed':
                    raise Exception(f"API вернул ошибку: {result['error']}")
            
            time.sleep(1)
        
        raise Exception(f"Таймаут ожидания результата для request_id {request_id}")
    
    def clear_result(self, request_id):
        """Удаляет результат из хранилища"""
        if request_id in self.callback_storage:
            del self.callback_storage[request_id]

# Глобальный экземпляр сервера
callback_server = None

def get_callback_server():
    """Получает глобальный экземпляр callback сервера"""
    global callback_server
    if callback_server is None:
        callback_server = CallbackServer()
        callback_server.start()
    return callback_server
