"""Инициализация Blueprint модулей для модульной архитектуры приложения.

Blueprint позволяют разделить приложение на логические модули:
- main_bp: основные страницы и маршруты
- news_api_bp: API для работы с новостями
- parser_api_bp: API для парсинга новостей из различных источников
- forecast_api_bp: API для прогнозирования и анализа
- external_api_bp: API для работы с внешними сервисами
"""

from app.blueprints.main import main_bp
from app.blueprints.news_api import news_api_bp
from app.blueprints.parser_api import parser_api_bp
from app.blueprints.forecast_api import forecast_api_bp
from app.blueprints.external_api import external_api_bp

# Экспортируем все Blueprint модули для использования в других частях приложения
__all__ = ['main_bp', 'news_api_bp', 'parser_api_bp', 'forecast_api_bp', 'external_api_bp']