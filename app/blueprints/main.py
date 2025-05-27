from flask import Blueprint, render_template

# Создаем Blueprint для основных маршрутов
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def base():
    return render_template('base.html')
    
@main_bp.route('/index')
def index():
    return render_template('home.html')

@main_bp.route('/analytics')
def analytics():
    return render_template('analytics.html')

@main_bp.route('/clickhouse')
def clickhouse():
    return render_template('database.html')

@main_bp.route('/reports')
def reports():
    return render_template('reports.html')

@main_bp.route('/predict')
def predict():
    return render_template('predict.html')

@main_bp.route('/trends')
def trends():
    return render_template('trends.html')

@main_bp.route('/archive')
def archive():
    return render_template('archive.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')