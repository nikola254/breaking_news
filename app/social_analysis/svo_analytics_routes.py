"""
Маршруты для аналитики СВО - статистика, графики и тренды
"""

from flask import Blueprint, render_template, jsonify, request
from datetime import datetime, timedelta
import logging
from ..analytics.svo_trends_analyzer import SVOTrendsAnalyzer, TrendData
from ..analytics.svo_visualizer import SVOVisualizer

logger = logging.getLogger(__name__)

svo_analytics_bp = Blueprint('svo_analytics', __name__)

@svo_analytics_bp.route('/svo-dashboard')
def svo_dashboard():
    """Главная страница дашборда аналитики СВО"""
    try:
        # Инициализация анализатора
        analyzer = SVOTrendsAnalyzer()
        visualizer = SVOVisualizer()
        
        # Генерация данных за период 2022-2025
        start_date = datetime(2022, 2, 24)  # Начало СВО
        end_date = datetime(2025, 1, 1)
        
        # Получение данных
        trend_data = analyzer.generate_synthetic_data(start_date, end_date)
        
        # Анализ трендов
        analysis_result = analyzer.analyze_trends(trend_data)
        
        # Корреляционный анализ
        correlations = analyzer.get_correlation_analysis(trend_data)
        
        # Сравнение периодов
        period_comparison = analyzer.get_period_comparison(trend_data)
        
        # Создание графиков
        charts = visualizer.create_dashboard_charts(trend_data)
        
        # Подготовка данных для шаблона
        dashboard_data = {
            'analysis_result': analysis_result,
            'correlations': correlations,
            'period_comparison': period_comparison,
            'charts': charts,
            'total_data_points': len(trend_data),
            'analysis_period': f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
        }
        
        return render_template('social_analysis/svo_dashboard.html', **dashboard_data)
        
    except Exception as e:
        logger.error(f"Ошибка в дашборде СВО: {e}")
        return render_template('error.html', 
                             error_message="Ошибка при загрузке дашборда аналитики СВО"), 500

@svo_analytics_bp.route('/api/svo-trends')
def api_svo_trends():
    """API для получения данных трендов СВО"""
    try:
        analyzer = SVOTrendsAnalyzer()
        
        # Параметры запроса
        start_date_str = request.args.get('start_date', '2022-02-24')
        end_date_str = request.args.get('end_date', '2025-01-01')
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Генерация данных
        trend_data = analyzer.generate_synthetic_data(start_date, end_date)
        
        # Преобразование в JSON-совместимый формат
        json_data = []
        for data_point in trend_data:
            json_data.append({
                'date': data_point.date.isoformat(),
                'interest_level': data_point.interest_level,
                'social_tension': data_point.social_tension,
                'mentions_count': data_point.mentions_count,
                'sentiment_score': data_point.sentiment_score,
                'keywords': data_point.keywords
            })
        
        return jsonify({
            'status': 'success',
            'data': json_data,
            'total_points': len(json_data)
        })
        
    except Exception as e:
        logger.error(f"Ошибка в API трендов СВО: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@svo_analytics_bp.route('/api/svo-analysis')
def api_svo_analysis():
    """API для получения результатов анализа СВО"""
    try:
        analyzer = SVOTrendsAnalyzer()
        
        # Параметры запроса
        start_date_str = request.args.get('start_date', '2022-02-24')
        end_date_str = request.args.get('end_date', '2025-01-01')
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Генерация и анализ данных
        trend_data = analyzer.generate_synthetic_data(start_date, end_date)
        analysis_result = analyzer.analyze_trends(trend_data)
        correlations = analyzer.get_correlation_analysis(trend_data)
        period_comparison = analyzer.get_period_comparison(trend_data)
        
        return jsonify({
            'status': 'success',
            'analysis': {
                'period_start': analysis_result.period_start.isoformat(),
                'period_end': analysis_result.period_end.isoformat(),
                'total_mentions': analysis_result.total_mentions,
                'avg_interest_level': analysis_result.avg_interest_level,
                'avg_social_tension': analysis_result.avg_social_tension,
                'trend_direction': analysis_result.trend_direction,
                'peak_dates': [date.isoformat() for date in analysis_result.peak_dates],
                'low_dates': [date.isoformat() for date in analysis_result.low_dates],
                'key_events': analysis_result.key_events
            },
            'correlations': correlations,
            'period_comparison': period_comparison
        })
        
    except Exception as e:
        logger.error(f"Ошибка в API анализа СВО: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@svo_analytics_bp.route('/api/svo-charts')
def api_svo_charts():
    """API для получения графиков СВО"""
    try:
        analyzer = SVOTrendsAnalyzer()
        visualizer = SVOVisualizer()
        
        # Параметры запроса
        chart_type = request.args.get('type', 'all')
        start_date_str = request.args.get('start_date', '2022-02-24')
        end_date_str = request.args.get('end_date', '2025-01-01')
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        # Генерация данных
        trend_data = analyzer.generate_synthetic_data(start_date, end_date)
        
        # Создание графиков
        charts = {}
        
        if chart_type == 'all' or chart_type == 'interest':
            charts['interest_dynamics'] = visualizer.create_interest_dynamics_chart(trend_data)
        
        if chart_type == 'all' or chart_type == 'tension':
            charts['social_tension'] = visualizer.create_social_tension_chart(trend_data)
        
        if chart_type == 'all' or chart_type == 'combined':
            charts['combined_trends'] = visualizer.create_combined_trends_chart(trend_data)
        
        if chart_type == 'all' or chart_type == 'correlation':
            charts['correlation_heatmap'] = visualizer.create_correlation_heatmap(trend_data)
        
        if chart_type == 'all' or chart_type == 'sentiment':
            charts['sentiment_analysis'] = visualizer.create_sentiment_analysis_chart(trend_data)
        
        if chart_type == 'all' or chart_type == 'mentions':
            charts['mentions_volume'] = visualizer.create_mentions_volume_chart(trend_data)
        
        return jsonify({
            'status': 'success',
            'charts': charts
        })
        
    except Exception as e:
        logger.error(f"Ошибка в API графиков СВО: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@svo_analytics_bp.route('/svo-report')
def svo_report():
    """Страница с подробным отчетом по анализу СВО"""
    try:
        analyzer = SVOTrendsAnalyzer()
        
        # Генерация данных
        start_date = datetime(2022, 2, 24)
        end_date = datetime(2025, 1, 1)
        trend_data = analyzer.generate_synthetic_data(start_date, end_date)
        
        # Анализ
        analysis_result = analyzer.analyze_trends(trend_data)
        correlations = analyzer.get_correlation_analysis(trend_data)
        period_comparison = analyzer.get_period_comparison(trend_data)
        
        # Подготовка отчета
        report_data = {
            'analysis_result': analysis_result,
            'correlations': correlations,
            'period_comparison': period_comparison,
            'trend_data_sample': trend_data[:10],  # Первые 10 точек для примера
            'total_data_points': len(trend_data)
        }
        
        return render_template('social_analysis/svo_report.html', **report_data)
        
    except Exception as e:
        logger.error(f"Ошибка в отчете СВО: {e}")
        return render_template('error.html', 
                             error_message="Ошибка при создании отчета СВО"), 500