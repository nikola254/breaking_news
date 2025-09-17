"""Инициализация Flask приложения для анализа новостей.

Этот модуль создает и настраивает Flask приложение с поддержкой:
- WebSocket соединений через Flask-SocketIO
- Модульной архитектуры через Blueprint
- Конфигурации из .env файла
"""

from flask import Flask
from flask_socketio import SocketIO
from config import Config

# Создаем Flask приложение
# static_folder='static' - папка для статических файлов (CSS, JS, изображения)
# static_url_path='/static' - статические файлы доступны по пути /static
app = Flask(__name__, static_folder='static', static_url_path='/static')
# Загружаем конфигурацию из класса Config
app.config.from_object(Config)

# Инициализируем SocketIO для real-time обновлений
# cors_allowed_origins="*" - разрешаем подключения с любых доменов
socketio = SocketIO(app, cors_allowed_origins="*")

# Импортируем и регистрируем Blueprint-модули для модульной архитектуры
from app.blueprints import main_bp, news_api_bp, parser_api_bp, forecast_api_bp, external_api_bp
from app.blueprints.chart_api import chart_api_bp
from app.blueprints.social_analysis import social_bp
from app.blueprints.ukraine_analytics_api import ukraine_analytics_bp


# Регистрируем все Blueprint модули
app.register_blueprint(main_bp)          # Основные страницы
app.register_blueprint(news_api_bp)      # API для работы с новостями
app.register_blueprint(parser_api_bp)    # API для парсинга новостей
app.register_blueprint(forecast_api_bp)  # API для прогнозирования
app.register_blueprint(external_api_bp)   # API для внешних сервисов
app.register_blueprint(chart_api_bp)       # API для создания графиков
app.register_blueprint(social_bp, url_prefix='/social-analysis')         # API для анализа социальных сетей
app.register_blueprint(ukraine_analytics_bp)  # API для украинской аналитики


# Инициализируем SocketIO в parser_api для real-time уведомлений
from app.blueprints.parser_api import init_socketio
init_socketio(socketio)

# Импортируем модели после инициализации приложения
from app import models