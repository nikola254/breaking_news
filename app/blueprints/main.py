"""Основные маршруты приложения для анализа новостей.

Этот Blueprint содержит все основные страницы пользовательского интерфейса.
Каждый маршрут отвечает за отображение соответствующей HTML страницы.
"""

from flask import Blueprint, render_template

# Создаем Blueprint для основных маршрутов
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def base():
    """Главная страница приложения.
    
    Returns:
        str: Отрендеренный HTML шаблон базовой страницы
    """
    return render_template('base.html')
    
@main_bp.route('/index')
def index():
    """Домашняя страница с обзором функций.
    
    Returns:
        str: Отрендеренный HTML шаблон домашней страницы
    """
    return render_template('home.html')

@main_bp.route('/analytics')
def analytics():
    """Страница аналитики новостей.
    
    Returns:
        str: Отрендеренный HTML шаблон страницы аналитики
    """
    return render_template('analytics.html')

@main_bp.route('/clickhouse')
def clickhouse():
    """Страница управления базой данных ClickHouse.
    
    Returns:
        str: Отрендеренный HTML шаблон страницы базы данных
    """
    return render_template('database.html')

@main_bp.route('/predict')
def predict():
    """Страница прогнозирования трендов.
    
    Returns:
        str: Отрендеренный HTML шаблон страницы прогнозирования
    """
    return render_template('predict.html')

@main_bp.route('/social-analysis')
def social_analysis():
    """Страница анализа социальных сетей.
    
    Returns:
        str: Отрендеренный HTML шаблон страницы анализа социальных сетей
    """
    return render_template('social_analysis.html')

@main_bp.route('/about')
def about():
    """Страница информации о приложении.
    
    Returns:
        str: Отрендеренный HTML шаблон страницы "О программе"
    """
    return render_template('about.html')
