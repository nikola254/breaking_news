"""API РґР»СЏ РїСЂРѕРіРЅРѕР·РёСЂРѕРІР°РЅРёСЏ Рё Р°РЅР°Р»РёР·Р° С‚СЂРµРЅРґРѕРІ РЅРѕРІРѕСЃС‚РµР№.

Р­С‚РѕС‚ РјРѕРґСѓР»СЊ СЃРѕРґРµСЂР¶РёС‚ С„СѓРЅРєС†РёРё РґР»СЏ:
- Р“РµРЅРµСЂР°С†РёРё РїСЂРѕРіРЅРѕР·РѕРІ РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё РЅРѕРІРѕСЃС‚РµР№
- РђРЅР°Р»РёР·Р° С‚СЂРµРЅРґРѕРІ РїРѕ РєР°С‚РµРіРѕСЂРёСЏРј
- РЎРѕР·РґР°РЅРёСЏ РІРёР·СѓР°Р»РёР·Р°С†РёР№ РґР°РЅРЅС‹С…
- РЎС‚Р°С‚РёСЃС‚РёС‡РµСЃРєРѕРіРѕ Р°РЅР°Р»РёР·Р° РЅРѕРІРѕСЃС‚РЅС‹С… РїРѕС‚РѕРєРѕРІ
"""

from flask import Blueprint, request, jsonify, current_app
import datetime
import random
import os
import matplotlib
matplotlib.use('Agg')  # РСЃРїРѕР»СЊР·СѓРµРј РЅРµ-РёРЅС‚РµСЂР°РєС‚РёРІРЅС‹Р№ Р±СЌРєРµРЅРґ
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import uuid
import requests
from clickhouse_driver import Client
from config import Config
from textblob import TextBlob
import re
from collections import Counter
from app.utils.ukraine_sentiment_analyzer import get_ukraine_sentiment_analyzer

# РЎРѕР·РґР°РµРј Blueprint РґР»СЏ API РїСЂРѕРіРЅРѕР·РѕРІ
forecast_api_bp = Blueprint('forecast_api', __name__, url_prefix='/api/forecast')

def get_clickhouse_client():
    """РЎРѕР·РґР°РЅРёРµ РєР»РёРµРЅС‚Р° РґР»СЏ РїРѕРґРєР»СЋС‡РµРЅРёСЏ Рє ClickHouse.
    
    Returns:
        Client: РќР°СЃС‚СЂРѕРµРЅРЅС‹Р№ РєР»РёРµРЅС‚ ClickHouse
    """
    return Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD,
        database=current_app.config.get('CLICKHOUSE_DB', 'default')
    )

def get_clickhouse_connection():
    """РџРѕР»СѓС‡РµРЅРёРµ СЃРѕРµРґРёРЅРµРЅРёСЏ СЃ ClickHouse"""
    try:
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            database=current_app.config.get('CLICKHOUSE_DB', 'default')
        )
        return client
    except Exception as e:
        print(f"РћС€РёР±РєР° РїРѕРґРєР»СЋС‡РµРЅРёСЏ Рє ClickHouse: {e}")
        return None

def get_military_keywords():
    """Р’РѕРµРЅРЅС‹Рµ РєР»СЋС‡РµРІС‹Рµ СЃР»РѕРІР° РґР»СЏ Р°РЅР°Р»РёР·Р°"""
    return {
        'military_operations': ['РЅР°СЃС‚СѓРїР»РµРЅРёРµ', 'Р°С‚Р°РєР°', 'РѕРїРµСЂР°С†РёСЏ', 'С€С‚СѓСЂРј', 'СѓРґР°СЂ', 'Р±РѕРјР±Р°СЂРґРёСЂРѕРІРєР°', 'РѕР±СЃС‚СЂРµР»'],
        'weapons': ['С‚Р°РЅРє', 'Р°СЂС‚РёР»Р»РµСЂРёСЏ', 'СЂР°РєРµС‚Р°', 'РґСЂРѕРЅ', 'Р°РІРёР°С†РёСЏ', 'РІРµСЂС‚РѕР»РµС‚', 'РёСЃС‚СЂРµР±РёС‚РµР»СЊ'],
        'locations': ['С„СЂРѕРЅС‚', 'РїРѕР·РёС†РёСЏ', 'СѓРєСЂРµРїР»РµРЅРёРµ', 'Р±Р°Р·Р°', 'Р°СЌСЂРѕРґСЂРѕРј', 'СЃРєР»Р°Рґ', 'РјРѕСЃС‚'],
        'personnel': ['СЃРѕР»РґР°С‚', 'РѕС„РёС†РµСЂ', 'РіРµРЅРµСЂР°Р»', 'РєРѕРјР°РЅРґРёСЂ', 'РІРѕРµРЅРЅС‹Р№', 'Р±РѕРµС†'],
        'escalation': ['РјРѕР±РёР»РёР·Р°С†РёСЏ', 'РїСЂРёР·С‹РІ', 'СЂРµР·РµСЂРІ', 'РїРѕРґРєСЂРµРїР»РµРЅРёРµ', 'СЌСЃРєР°Р»Р°С†РёСЏ']
    }

def analyze_sentiment(text):
    """РђРЅР°Р»РёР· С‚РѕРЅР°Р»СЊРЅРѕСЃС‚Рё С‚РµРєСЃС‚Р° СЃ РёСЃРїРѕР»СЊР·РѕРІР°РЅРёРµРј СѓРєСЂР°РёРЅСЃРєРѕРіРѕ Р°РЅР°Р»РёР·Р°С‚РѕСЂР°"""
    try:
        # РСЃРїРѕР»СЊР·СѓРµРј СЃРїРµС†РёР°Р»РёР·РёСЂРѕРІР°РЅРЅС‹Р№ Р°РЅР°Р»РёР·Р°С‚РѕСЂ РґР»СЏ СѓРєСЂР°РёРЅСЃРєРёС… РЅРѕРІРѕСЃС‚РµР№
        analyzer = get_ukraine_sentiment_analyzer()
        result = analyzer.analyze_sentiment(text)
        return analyzer.get_sentiment_category(result['sentiment_score'])
    except Exception as e:
        print(f"РћС€РёР±РєР° Р°РЅР°Р»РёР·Р° С‚РѕРЅР°Р»СЊРЅРѕСЃС‚Рё: {e}")
        return 'neutral'

def calculate_tension_index(news_data, military_keywords):
    """Р Р°СЃС‡РµС‚ РёРЅРґРµРєСЃР° РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё"""
    if not news_data:
        return 0.5
    
    tension_score = 0
    total_weight = 0
    
    for article in news_data:
        text = (article.get('title', '') + ' ' + article.get('content', '')).lower()
        
        # РџРѕРґСЃС‡РµС‚ РІРѕРµРЅРЅС‹С… РєР»СЋС‡РµРІС‹С… СЃР»РѕРІ
        military_count = 0
        for category, keywords in military_keywords.items():
            for keyword in keywords:
                military_count += text.count(keyword)
        
        # РђРЅР°Р»РёР· С‚РѕРЅР°Р»СЊРЅРѕСЃС‚Рё
        sentiment = analyze_sentiment(text)
        sentiment_weight = {'negative': 1.0, 'neutral': 0.5, 'positive': 0.2}[sentiment]
        
        # Р Р°СЃС‡РµС‚ РІРµСЃР° СЃС‚Р°С‚СЊРё
        article_weight = 1 + (military_count * 0.1)
        
        # Р‘Р°Р·РѕРІС‹Р№ СѓСЂРѕРІРµРЅСЊ РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё
        base_tension = 0.3 + (military_count * 0.05)
        article_tension = min(1.0, base_tension * sentiment_weight)
        
        tension_score += article_tension * article_weight
        total_weight += article_weight
    
    return min(1.0, tension_score / total_weight if total_weight > 0 else 0.5)

def extract_key_topics(news_data, limit=10):
    """РР·РІР»РµС‡РµРЅРёРµ РєР»СЋС‡РµРІС‹С… С‚РµРј"""
    if not news_data:
        return []
    
    # РћР±СЉРµРґРёРЅСЏРµРј РІСЃРµ С‚РµРєСЃС‚С‹
    all_text = ' '.join([article.get('title', '') + ' ' + article.get('content', '') for article in news_data])
    
    # РџСЂРѕСЃС‚РѕРµ РёР·РІР»РµС‡РµРЅРёРµ РєР»СЋС‡РµРІС‹С… СЃР»РѕРІ
    words = re.findall(r'\b[Р°-СЏС‘]{4,}\b', all_text.lower())
    
    # РСЃРєР»СЋС‡Р°РµРј СЃС‚РѕРї-СЃР»РѕРІР°
    stop_words = {'РєРѕС‚РѕСЂС‹Р№', 'РєРѕС‚РѕСЂР°СЏ', 'РєРѕС‚РѕСЂС‹Рµ', 'С‚Р°РєР¶Рµ', 'Р±РѕР»РµРµ', 'РјРѕР¶РµС‚', 'РґРѕР»Р¶РµРЅ', 'РїРѕСЃР»Рµ', 'РІСЂРµРјСЏ'}
    words = [word for word in words if word not in stop_words]
    
    # РџРѕРґСЃС‡РёС‚С‹РІР°РµРј С‡Р°СЃС‚РѕС‚Сѓ
    word_counts = Counter(words)
    
    # Р’РѕР·РІСЂР°С‰Р°РµРј С‚РѕРї С‚РµРј СЃ РІРµСЃР°РјРё
    topics = []
    for word, count in word_counts.most_common(limit):
        weight = min(1.0, count / len(news_data))
        topics.append({'topic': word, 'weight': weight})
    
    return topics

def generate_military_forecast(category, tension_index, topics, forecast_days):
    """Р“РµРЅРµСЂР°С†РёСЏ РІРѕРµРЅРЅРѕРіРѕ РїСЂРѕРіРЅРѕР·Р°"""
    if category not in ['ukraine', 'middle_east'] or tension_index < 0.6:
        return None
    
    # РћРїСЂРµРґРµР»СЏРµРј РІРµСЂРѕСЏС‚РЅС‹Рµ РЅР°РїСЂР°РІР»РµРЅРёСЏ
    directions = {
        'ukraine': ['РҐР°СЂСЊРєРѕРІСЃРєРѕРµ', 'Р—Р°РїРѕСЂРѕР¶СЃРєРѕРµ', 'РҐРµСЂСЃРѕРЅСЃРєРѕРµ', 'Р”РѕРЅРµС†РєРѕРµ'],
        'middle_east': ['Р“Р°Р·Р°', 'Р—Р°РїР°РґРЅС‹Р№ Р±РµСЂРµРі', 'Р›РёРІР°РЅ', 'РЎРёСЂРёСЏ']
    }
    
    # Р“РµРЅРµСЂРёСЂСѓРµРј РїСЂРѕРіРЅРѕР· РЅР° РѕСЃРЅРѕРІРµ СѓСЂРѕРІРЅСЏ РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё
    forecast = {
        'overall_assessment': {
            'tension_level': 'РІС‹СЃРѕРєРёР№' if tension_index > 0.8 else 'СЃСЂРµРґРЅРёР№',
            'probability_escalation': min(95, int(tension_index * 100)),
            'risk_level': 'РєСЂРёС‚РёС‡РµСЃРєРёР№' if tension_index > 0.9 else 'РїРѕРІС‹С€РµРЅРЅС‹Р№'
        },
        'probable_actions': [],
        'risk_areas': directions.get(category, [])[:3],
        'timeline': {
            'short_term': f'1-{min(7, forecast_days)} РґРЅРµР№',
            'medium_term': f'{min(7, forecast_days)}-{min(30, forecast_days)} РґРЅРµР№'
        },
        'recommendations': [
            'РЈСЃРёР»РµРЅРёРµ РјРѕРЅРёС‚РѕСЂРёРЅРіР° СЃРёС‚СѓР°С†РёРё',
            'РџРѕРґРіРѕС‚РѕРІРєР° Рє РІРѕР·РјРѕР¶РЅРѕР№ СЌСЃРєР°Р»Р°С†РёРё',
            'РљРѕРѕСЂРґРёРЅР°С†РёСЏ СЃ СЃРѕСЋР·РЅРёРєР°РјРё'
        ]
    }
    
    # Р”РѕР±Р°РІР»СЏРµРј РІРµСЂРѕСЏС‚РЅС‹Рµ РґРµР№СЃС‚РІРёСЏ РЅР° РѕСЃРЅРѕРІРµ С‚РµРј
    if any('РЅР°СЃС‚СѓРїР»РµРЅРёРµ' in topic['topic'] for topic in topics):
        forecast['probable_actions'].append('РџРѕРґРіРѕС‚РѕРІРєР° РЅР°СЃС‚СѓРїР°С‚РµР»СЊРЅС‹С… РѕРїРµСЂР°С†РёР№')
    if any('РѕР±РѕСЂРѕРЅР°' in topic['topic'] for topic in topics):
        forecast['probable_actions'].append('РЈРєСЂРµРїР»РµРЅРёРµ РѕР±РѕСЂРѕРЅРёС‚РµР»СЊРЅС‹С… РїРѕР·РёС†РёР№')
    if any('Р°РІРёР°С†РёСЏ' in topic['topic'] for topic in topics):
        forecast['probable_actions'].append('РђРєС‚РёРІРёР·Р°С†РёСЏ Р°РІРёР°С†РёРѕРЅРЅС‹С… СѓРґР°СЂРѕРІ')
    
    return forecast

def perform_real_analysis(category, analysis_period, forecast_period):
    """Р’С‹РїРѕР»РЅРµРЅРёРµ СЂРµР°Р»СЊРЅРѕРіРѕ Р°РЅР°Р»РёР·Р° РґР°РЅРЅС‹С…"""
    try:
        client = get_clickhouse_connection()
        if not client:
            return None
        
        # РџРѕР»СѓС‡Р°РµРј СЃРїРёСЃРѕРє РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёС… С‚Р°Р±Р»РёС†
        custom_tables_query = """
            SELECT name 
            FROM system.tables 
            WHERE database = 'news' 
            AND name LIKE 'custom_%_headlines'
        """
        custom_tables = client.execute(custom_tables_query)
        custom_unions = []
        
        for table in custom_tables:
            table_name = table[0]
            custom_unions.append(f"SELECT title, content, published_date, category FROM news.{table_name}")
        
        # Р¤РѕСЂРјРёСЂСѓРµРј Р·Р°РїСЂРѕСЃ РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ РєР°С‚РµРіРѕСЂРёРё
        if category == 'all':
            category_filter = ""
        else:
            category_filter = f"AND category = '{category}'"
        
        # РџРѕР»СѓС‡Р°РµРј РґР°РЅРЅС‹Рµ Р·Р° РїРµСЂРёРѕРґ Р°РЅР°Р»РёР·Р° РёР· РІСЃРµС… С‚Р°Р±Р»РёС†
        # Р¤РѕСЂРјРёСЂСѓРµРј СЃРїРёСЃРѕРє РІСЃРµС… С‚Р°Р±Р»РёС† (СЃС‚Р°РЅРґР°СЂС‚РЅС‹Рµ + РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ)
        all_unions = [
            "SELECT title, content, published_date, category FROM news.ria_headlines",
            "SELECT title, content, published_date, category FROM news.bbc_headlines",
            "SELECT title, content, published_date, category FROM news.cnn_headlines",
            "SELECT title, content, published_date, category FROM news.reuters_headlines",
            "SELECT title, content, published_date, category FROM news.france24_headlines",
            "SELECT title, content, published_date, category FROM news.aljazeera_headlines",
            "SELECT title, content, published_date, category FROM news.euronews_headlines",
            "SELECT title, content, published_date, category FROM news.dw_headlines",
            "SELECT title, content, published_date, category FROM news.rt_headlines",
            "SELECT title, content, published_date, category FROM news.gazeta_headlines",
            "SELECT title, content, published_date, category FROM news.lenta_headlines",
            "SELECT title, content, published_date, category FROM news.kommersant_headlines",
            "SELECT title, content, published_date, category FROM news.rbc_headlines",
            "SELECT title, content, published_date, category FROM news.tsn_headlines",
            "SELECT title, content, published_date, category FROM news.unian_headlines",
            "SELECT title, content, published_date, category FROM news.israil_headlines",
            "SELECT title, content, published_date, category FROM news.telegram_headlines"
        ]
        
        # Р”РѕР±Р°РІР»СЏРµРј РїРѕР»СЊР·РѕРІР°С‚РµР»СЊСЃРєРёРµ С‚Р°Р±Р»РёС†С‹
        all_unions.extend(custom_unions)
        
        query = f"""
        SELECT title, content, published_date as published_date, category
        FROM (
            {' UNION ALL '.join(all_unions)}
        ) as all_news
        WHERE published_date >= now() - INTERVAL {analysis_period} HOUR
        {category_filter}
        ORDER BY published_date DESC
        LIMIT 1000
        """
        
        news_data = client.execute(query)
        
        if not news_data:
            return None
        
        # РџСЂРµРѕР±СЂР°Р·СѓРµРј РІ СЃРїРёСЃРѕРє СЃР»РѕРІР°СЂРµР№
        articles = []
        for row in news_data:
            articles.append({
                'title': row[0],
                'content': row[1],
                'published_date': row[2],
                'category': row[3]
            })
        
        # РђРЅР°Р»РёР·РёСЂСѓРµРј РґР°РЅРЅС‹Рµ
        military_keywords = get_military_keywords()
        tension_index = calculate_tension_index(articles, military_keywords)
        topics = extract_key_topics(articles)
        
        # Р“РµРЅРµСЂРёСЂСѓРµРј РїСЂРѕРіРЅРѕР· РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё
        forecast_days = max(1, forecast_period // 24)
        today = datetime.datetime.now()
        tension_values = []
        
        # РџСЂРѕРіРЅРѕР·РёСЂСѓРµРј РёР·РјРµРЅРµРЅРёРµ РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё
        base_trend = (tension_index - 0.5) * 0.1  # РўСЂРµРЅРґ РЅР° РѕСЃРЅРѕРІРµ С‚РµРєСѓС‰РµРіРѕ СѓСЂРѕРІРЅСЏ
        
        for i in range(forecast_days):
            date = today + datetime.timedelta(days=i)
            
            # Р”РѕР±Р°РІР»СЏРµРј СЃР»СѓС‡Р°Р№РЅС‹Рµ РєРѕР»РµР±Р°РЅРёСЏ Рё С‚СЂРµРЅРґ
            daily_variation = np.random.normal(0, 0.03)
            trend_component = base_trend * (i / forecast_days)
            
            predicted_tension = tension_index + trend_component + daily_variation
            predicted_tension = max(0.1, min(1.0, predicted_tension))
            
            # Р”РѕРІРµСЂРёС‚РµР»СЊРЅС‹Рµ РёРЅС‚РµСЂРІР°Р»С‹
            confidence = 0.95 - (i * 0.02)  # РЈРјРµРЅСЊС€Р°РµРј СѓРІРµСЂРµРЅРЅРѕСЃС‚СЊ СЃРѕ РІСЂРµРјРµРЅРµРј
            margin = (1 - confidence) * 0.2
            
            tension_values.append({
                'date': date.strftime('%d.%m.%Y'),
                'value': predicted_tension,
                'lower_bound': max(0.1, predicted_tension - margin),
                'upper_bound': min(1.0, predicted_tension + margin)
            })
        
        # Р“РµРЅРµСЂРёСЂСѓРµРј РІРѕРµРЅРЅС‹Р№ РїСЂРѕРіРЅРѕР· РµСЃР»Рё РїСЂРёРјРµРЅРёРјРѕ
        military_forecast = generate_military_forecast(category, tension_index, topics, forecast_days)
        
        return {
            'news_count': len(articles),
            'tension_index': tension_index,
            'tension_forecast': {
                'values': tension_values,
                'trend': 'СЂР°СЃС‚СѓС‰РёР№' if base_trend > 0 else 'СЃРЅРёР¶Р°СЋС‰РёР№СЃСЏ' if base_trend < 0 else 'СЃС‚Р°Р±РёР»СЊРЅС‹Р№'
            },
            'topics_forecast': {
                'topics': topics,
                'analysis_period': f'{analysis_period} С‡Р°СЃРѕРІ'
            },
            'military_forecast': military_forecast
        }
        
    except Exception as e:
        print(f"РћС€РёР±РєР° Р°РЅР°Р»РёР·Р°: {e}")
        return None

def generate_ai_forecast(analysis_data, category, analysis_period, forecast_period):
    """Генерация детального прогноза с использованием AI модели
    
    Args:
        analysis_data (dict): Данные анализа из ClickHouse
        category (str): Категория новостей
        analysis_period (int): Период анализа в часах
        forecast_period (int): Период прогноза в часах
    
    Returns:
        dict: Детальный прогноз от AI или None при ошибке
    """
    try:
        # Импортируем GenApiNewsClassifier
        from parsers.gen_api_classifier import GenApiNewsClassifier
        
        # Получаем API ключ из конфигурации
        api_key = current_app.config.get('GEN_API_KEY')
        
        if not api_key:
            current_app.logger.warning("GEN_API_KEY не найден, используем fallback прогноз")
            return None
        
        # Формируем детальный промпт для AI
        news_count = analysis_data.get('news_count', 0)
        tension_index = analysis_data.get('tension_index', 0.5)
        topics = analysis_data.get('topics_forecast', {}).get('topics', [])
        
        # Определяем уровень напряженности
        if tension_index >= 0.8:
            tension_level = "критический"
        elif tension_index >= 0.6:
            tension_level = "высокий"
        elif tension_index >= 0.4:
            tension_level = "средний"
        else:
            tension_level = "низкий"
        
        # Формируем список основных тем
        topics_text = ""
        if topics:
            topics_text = ", ".join([f"{topic.get('topic', 'неизвестная тема')} ({topic.get('weight', 0):.1%})" for topic in topics[:5]])
        
        prompt = f"""Ты эксперт по анализу социальной напряженности и прогнозированию конфликтов. 

АНАЛИЗИРУЕМЫЕ ДАННЫЕ:
- Категория: {get_category_name(category)}
- Период анализа: {analysis_period} часов
- Период прогноза: {forecast_period} часов
- Количество проанализированных новостей: {news_count}
- Текущий индекс напряженности: {tension_index:.1%} ({tension_level})
- Основные темы: {topics_text}

ЗАДАЧА: Создай детальный прогноз развития ситуации в следующем формате:

📊 АНАЛИЗ ТЕКУЩЕЙ СИТУАЦИИ
- Количество проанализированных новостей: {news_count}
- Текущий индекс напряженности: {tension_index:.1%} (категория: {tension_level})
- Динамика за период: [растущая/стабильная/снижающаяся]
- Основные темы: {topics_text}

🔮 ПРОГНОЗ РАЗВИТИЯ НА {forecast_period} ЧАСОВ
[Детальный прогноз с разбивкой по дням и конкретными цифрами напряженности]

⚡ КЛЮЧЕВЫЕ ФАКТОРЫ ВЛИЯНИЯ
1. [Фактор 1]: влияние [X]%
2. [Фактор 2]: влияние [X]%
3. [Фактор 3]: влияние [X]%

🎯 СЦЕНАРИИ РАЗВИТИЯ СОБЫТИЙ
🟢 Оптимистичный (вероятность [X]%):
   [Детальное описание сценария с обоснованием]
   
🟡 Реалистичный (вероятность [X]%):
   [Детальное описание сценария с обоснованием]
   
🔴 Пессимистичный (вероятность [X]%):
   [Детальное описание сценария с обоснованием]

💡 РЕКОМЕНДАЦИИ
- [Рекомендация 1]
- [Рекомендация 2]
- [Рекомендация 3]

Отвечай только в указанном формате, используй конкретные цифры и обоснования."""

        # Создаем классификатор и отправляем запрос
        classifier = GenApiNewsClassifier(api_key=api_key)
        
        # Используем новый метод generate_forecast вместо classify
        result = classifier.generate_forecast(prompt, max_tokens=2000)
        
        return {
            'ai_forecast': result['forecast'],
            'api_used': 'gen-api.ru',
            'tokens_used': result['tokens_used']
        }
            
    except Exception as e:
        current_app.logger.error(f"Ошибка AI прогнозирования: {e}")
        return None

def generate_fallback_topics(category):
    """Р“РµРЅРµСЂР°С†РёСЏ С‚РµРј РїРѕ СѓРјРѕР»С‡Р°РЅРёСЋ РґР»СЏ РєР°С‚РµРіРѕСЂРёРё"""
    topics_by_category = {
        'military_operations': [
            {'topic': 'Р±РѕРµРІС‹Рµ РґРµР№СЃС‚РІРёСЏ', 'weight': 0.9},
            {'topic': 'РІРѕРµРЅРЅР°СЏ С‚РµС…РЅРёРєР°', 'weight': 0.7},
            {'topic': 'РїРѕС‚РµСЂРё', 'weight': 0.6}
        ],
        'political_decisions': [
            {'topic': 'РїРµСЂРµРіРѕРІРѕСЂС‹', 'weight': 0.8},
            {'topic': 'РґРёРїР»РѕРјР°С‚РёСЏ', 'weight': 0.7},
            {'topic': 'СЃР°РЅРєС†РёРё', 'weight': 0.6}
        ],
        'economic_consequences': [
            {'topic': 'СЌРєРѕРЅРѕРјРёС‡РµСЃРєРёРµ РїРѕС‚РµСЂРё', 'weight': 0.8},
            {'topic': 'СЌРЅРµСЂРіРµС‚РёРєР°', 'weight': 0.7},
            {'topic': 'С‚РѕСЂРіРѕРІР»СЏ', 'weight': 0.5}
        ],
        'humanitarian_crisis': [
            {'topic': 'Р±РµР¶РµРЅС†С‹', 'weight': 0.9},
            {'topic': 'РіСѓРјР°РЅРёС‚Р°СЂРЅР°СЏ РїРѕРјРѕС‰СЊ', 'weight': 0.8},
            {'topic': 'Р¶РµСЂС‚РІС‹ СЃСЂРµРґРё РјРёСЂРЅРѕРіРѕ РЅР°СЃРµР»РµРЅРёСЏ', 'weight': 0.7}
        ],
        'information_social': [
            {'topic': 'РёРЅС„РѕСЂРјР°С†РёРѕРЅРЅР°СЏ РІРѕР№РЅР°', 'weight': 0.8},
            {'topic': 'РїСЂРѕРїР°РіР°РЅРґР°', 'weight': 0.7},
            {'topic': 'РѕР±С‰РµСЃС‚РІРµРЅРЅРѕРµ РјРЅРµРЅРёРµ', 'weight': 0.6}
        ],
        'all': [
            {'topic': 'РІРѕРµРЅРЅС‹Рµ РґРµР№СЃС‚РІРёСЏ', 'weight': 0.8},
            {'topic': 'РїРѕР»РёС‚РёС‡РµСЃРєРёРµ СЃРѕР±С‹С‚РёСЏ', 'weight': 0.7},
            {'topic': 'РіСѓРјР°РЅРёС‚Р°СЂРЅР°СЏ СЃРёС‚СѓР°С†РёСЏ', 'weight': 0.6}
        ]
    }
    
    return topics_by_category.get(category, topics_by_category['all'])

@forecast_api_bp.route('/generate_forecast', methods=['POST'])
def generate_forecast():
    """Р“РµРЅРµСЂР°С†РёСЏ РїСЂРѕРіРЅРѕР·Р° РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё РЅРѕРІРѕСЃС‚РµР№.
    
    РђРЅР°Р»РёР·РёСЂСѓРµС‚ РёСЃС‚РѕСЂРёС‡РµСЃРєРёРµ РґР°РЅРЅС‹Рµ Рё СЃРѕР·РґР°РµС‚ РїСЂРѕРіРЅРѕР·
    РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё РЅРѕРІРѕСЃС‚РµР№ РЅР° СѓРєР°Р·Р°РЅРЅС‹Р№ РїРµСЂРёРѕРґ.
    
    Request JSON:
        category (str): РљР°С‚РµРіРѕСЂРёСЏ РЅРѕРІРѕСЃС‚РµР№ РґР»СЏ Р°РЅР°Р»РёР·Р°
        analysis_period (int): РџРµСЂРёРѕРґ Р°РЅР°Р»РёР·Р° РІ С‡Р°СЃР°С…
        forecast_period (int): РџРµСЂРёРѕРґ РїСЂРѕРіРЅРѕР·Р° РІ С‡Р°СЃР°С…
    
    Returns:
        JSON: РџСЂРѕРіРЅРѕР· СЃ РґР°РЅРЅС‹РјРё Рё РїСѓС‚РµРј Рє РіСЂР°С„РёРєСѓ
    """
    try:
        data = request.json
        category = data.get('category', 'all')
        analysis_period = data.get('analysis_period', 24)  # в часах
        forecast_period = data.get('forecast_period', 24)  # в часах
        prompt = data.get('prompt', '')  # Добавить опциональный параметр
        
        # Преобразуем период прогноза в дни для совместимости с текущим кодом
        forecast_days = max(1, forecast_period // 24)
        
        # Используем реальный анализ данных из ClickHouse
        analysis_result = perform_real_analysis(category, analysis_period, forecast_period)
        
        # Генерируем AI прогноз если есть данные анализа
        ai_forecast_data = None
        if analysis_result:
            ai_forecast_data = generate_ai_forecast(analysis_result, category, analysis_period, forecast_period)
        
        # Если нет AI прогноза, возвращаем ошибку вместо пустого скелета
        if not ai_forecast_data:
            return jsonify({
                'status': 'error', 
                'message': 'AI прогноз недоступен. Проверьте настройки GEN_API_KEY или попробуйте позже.'
            }), 500
        
        # Если предоставлен prompt, можно использовать AI для уточнения прогноза
        ai_response = None
        if prompt:
            # Интеграция с AI для улучшения прогноза
            try:
                # Здесь можно добавить вызов AI API для обработки prompt
                # Пока что просто сохраняем prompt как дополнительную информацию
                ai_response = f"Пользовательский запрос: {prompt}"
            except Exception as e:
                current_app.logger.warning(f"AI integration failed: {e}")
        
        if analysis_result:
            tension_values = analysis_result['tension_forecast']['values']
            topics_data = analysis_result['topics_forecast']['topics']
            military_forecast = analysis_result.get('military_forecast')
        else:
            # Fallback Рє РіРµРЅРµСЂР°С†РёРё РґР°РЅРЅС‹С…, РµСЃР»Рё Р°РЅР°Р»РёР· РЅРµ СѓРґР°Р»СЃСЏ
            today = datetime.datetime.now()
            tension_values = []
            
            # Р‘Р°Р·РѕРІС‹Р№ СѓСЂРѕРІРµРЅСЊ РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ РєР°С‚РµРіРѕСЂРёРё
            base_tension = {
                'all': 0.5,
                'military_operations': 0.8,
                'political_decisions': 0.7,
                'economic_consequences': 0.6,
                'humanitarian_crisis': 0.75,
                'information_social': 0.65
            }.get(category, 0.5)
            
            # Р“РµРЅРµСЂРёСЂСѓРµРј Р·РЅР°С‡РµРЅРёСЏ СЃ С‚СЂРµРЅРґРѕРј
            trend = random.uniform(-0.1, 0.1)  # РЎР»СѓС‡Р°Р№РЅС‹Р№ С‚СЂРµРЅРґ
            
            for i in range(forecast_days):
                date = today + datetime.timedelta(days=i)
                # Р”РѕР±Р°РІР»СЏРµРј СЃР»СѓС‡Р°Р№РЅС‹Рµ РєРѕР»РµР±Р°РЅРёСЏ Рё С‚СЂРµРЅРґ
                noise = random.uniform(-0.05, 0.05)
                trend_component = trend * i / forecast_days
                value = min(1.0, max(0.1, base_tension + noise + trend_component))
                
                tension_values.append({
                    'date': date.strftime('%d.%m.%Y'),
                    'value': value,
                    'lower_bound': max(0.1, value - random.uniform(0.03, 0.08)),
                    'upper_bound': min(1.0, value + random.uniform(0.03, 0.08))
                })
            
            topics_data = generate_fallback_topics(category)
            military_forecast = None
        
        # РСЃРїРѕР»СЊР·СѓРµРј РґР°РЅРЅС‹Рµ РёР· СЂРµР°Р»СЊРЅРѕРіРѕ Р°РЅР°Р»РёР·Р° РёР»Рё fallback
        if not analysis_result:
            topics_data = generate_fallback_topics(category)
        
        # РўРµРјС‹ РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ РєР°С‚РµРіРѕСЂРёРё
        topics_by_category = {
            'ukraine': [
                {'name': 'Р’РѕРµРЅРЅС‹Рµ РґРµР№СЃС‚РІРёСЏ', 'value': random.uniform(0.4, 0.6), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Р”РёРїР»РѕРјР°С‚РёСЏ', 'value': random.uniform(0.2, 0.3), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Р“СѓРјР°РЅРёС‚Р°СЂРЅР°СЏ СЃРёС‚СѓР°С†РёСЏ', 'value': random.uniform(0.1, 0.2), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Р­РєРѕРЅРѕРјРёРєР°', 'value': random.uniform(0.05, 0.15), 'change': random.uniform(-0.05, 0.05)},
                {'name': 'Р”СЂСѓРіРѕРµ', 'value': random.uniform(0.05, 0.1), 'change': random.uniform(-0.05, 0.05)}
            ],
            'middle_east': [
                {'name': 'РљРѕРЅС„Р»РёРєС‚ РР·СЂР°РёР»СЊ-РџР°Р»РµСЃС‚РёРЅР°', 'value': random.uniform(0.3, 0.5), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'РСЂР°РЅ', 'value': random.uniform(0.2, 0.3), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'РЎРёСЂРёСЏ', 'value': random.uniform(0.1, 0.2), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Р™РµРјРµРЅ', 'value': random.uniform(0.05, 0.15), 'change': random.uniform(-0.05, 0.05)},
                {'name': 'Р”СЂСѓРіРѕРµ', 'value': random.uniform(0.05, 0.1), 'change': random.uniform(-0.05, 0.05)}
            ],
            'fake_news': [
                {'name': 'Р”РµР·РёРЅС„РѕСЂРјР°С†РёСЏ', 'value': random.uniform(0.3, 0.5), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'РњР°РЅРёРїСѓР»СЏС†РёРё', 'value': random.uniform(0.2, 0.4), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Р¤РµР№РєРѕРІС‹Рµ Р°РєРєР°СѓРЅС‚С‹', 'value': random.uniform(0.1, 0.2), 'change': random.uniform(-0.1, 0.1)},
                {'name': 'Р”СЂСѓРіРѕРµ', 'value': random.uniform(0.05, 0.15), 'change': random.uniform(-0.05, 0.05)}
            ]
        }
        
        # Формируем ответ только с AI прогнозом
        response_data = {
            'status': 'success',
            'forecast_data': {
                'tension_forecast': {
                    'values': tension_values,
                    'trend': analysis_result.get('tension_forecast', {}).get('trend', 'стабильный') if analysis_result else 'неопределенный'
                },
                'topics_forecast': {
                    'topics': topics_data
                },
                'ai_forecast': ai_forecast_data['ai_forecast']
            },
            'metadata': {
                'category': category,
                'analysis_period': f'{analysis_period} часов',
                'forecast_period': f'{forecast_period} часов',
                'news_analyzed': analysis_result.get('news_count', 0) if analysis_result else 0,
                'tension_index': round(analysis_result.get('tension_index', 0.5) if analysis_result else 0.5, 3),
                'ai_api_used': ai_forecast_data.get('api_used', 'unknown'),
                'ai_tokens_used': ai_forecast_data.get('tokens_used', 0)
            }
        }
        
        # Добавляем AI ответ если он есть
        if ai_response:
            response_data['ai_response'] = ai_response
        
        # Добавляем военный прогноз если он есть
        if analysis_result and analysis_result.get('military_forecast'):
            response_data['forecast_data']['military_forecast'] = analysis_result['military_forecast']
        
        return jsonify(response_data)
    except Exception as e:
        current_app.logger.error(f"Error generating forecast: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Р¤СѓРЅРєС†РёСЏ РґР»СЏ РіРµРЅРµСЂР°С†РёРё РіСЂР°С„РёРєР° РїСЂРѕРіРЅРѕР·Р° РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё
def generate_tension_chart(tension_values, category):
    plt.figure(figsize=(10, 6))
    sns.set_style("whitegrid")
    
    dates = [item['date'] for item in tension_values]
    values = [item['value'] for item in tension_values]
    lower_bounds = [item['lower_bound'] for item in tension_values]
    upper_bounds = [item['upper_bound'] for item in tension_values]
    
    plt.plot(dates, values, marker='o', linewidth=2, color='#1976D2', label='РРЅРґРµРєСЃ РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё')
    plt.fill_between(dates, lower_bounds, upper_bounds, color='#1976D2', alpha=0.2, label='Р”РёР°РїР°Р·РѕРЅ РїСЂРѕРіРЅРѕР·Р°')
    
    plt.title(f'РџСЂРѕРіРЅРѕР· РёРЅРґРµРєСЃР° СЃРѕС†РёР°Р»СЊРЅРѕР№ РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё: {get_category_name(category)}')
    plt.xlabel('Р”Р°С‚Р°')
    plt.ylabel('РРЅРґРµРєСЃ РЅР°РїСЂСЏР¶РµРЅРЅРѕСЃС‚Рё')
    plt.ylim(0, 1)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.legend()
    
    # РЎРѕС…СЂР°РЅСЏРµРј РіСЂР°С„РёРє
    unique_id = uuid.uuid4().hex[:8]
    today_str = datetime.datetime.now().strftime('%Y%m%d')
    filename = f'tension_forecast_{category}_{today_str}_{unique_id}.png'
    
    static_folder = os.path.join(current_app.root_path, 'static', 'images')
    os.makedirs(static_folder, exist_ok=True)
    
    filepath = os.path.join(static_folder, filename)
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()
    
    return f'/static/images/{filename}'

# Р¤СѓРЅРєС†РёСЏ РґР»СЏ РіРµРЅРµСЂР°С†РёРё РіСЂР°С„РёРєР° СЂР°СЃРїСЂРµРґРµР»РµРЅРёСЏ С‚РµРј
def generate_topics_chart(topics, category):
    plt.figure(figsize=(10, 6))
    sns.set_style("whitegrid")
    
    names = [item['name'] for item in topics]
    values = [item['value'] for item in topics]
    changes = [item['change'] for item in topics]
    
    # Р¦РІРµС‚Р° РІ Р·Р°РІРёСЃРёРјРѕСЃС‚Рё РѕС‚ РёР·РјРµРЅРµРЅРёСЏ (РєСЂР°СЃРЅС‹Р№ - РЅРµРіР°С‚РёРІРЅРѕРµ, Р·РµР»РµРЅС‹Р№ - РїРѕР·РёС‚РёРІРЅРѕРµ)
    colors = ['#4CAF50' if change >= 0 else '#F44336' for change in changes]
    
    bars = plt.bar(names, values, color=colors)
    
    # Р”РѕР±Р°РІР»СЏРµРј Р°РЅРЅРѕС‚Р°С†РёРё СЃ РїСЂРѕС†РµРЅС‚Р°РјРё Рё РёР·РјРµРЅРµРЅРёСЏРјРё
    for i, bar in enumerate(bars):
        height = bar.get_height()
        change = changes[i]
        change_symbol = 'в†‘' if change > 0 else 'в†“' if change < 0 else 'в†’'
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                f'{values[i]:.1%}\n{change_symbol}{abs(change):.1%}',
                ha='center', va='bottom', fontsize=9)
    
    plt.title(f'Р Р°СЃРїСЂРµРґРµР»РµРЅРёРµ С‚РµРј: {get_category_name(category)}')
    plt.xlabel('РўРµРјС‹')
    plt.ylabel('Р”РѕР»СЏ')
    plt.ylim(0, max(values) * 1.3)  # РћСЃС‚Р°РІР»СЏРµРј РјРµСЃС‚Рѕ РґР»СЏ Р°РЅРЅРѕС‚Р°С†РёР№
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # РЎРѕС…СЂР°РЅСЏРµРј РіСЂР°С„РёРє
    unique_id = uuid.uuid4().hex[:8]
    today_str = datetime.datetime.now().strftime('%Y%m%d')
    filename = f'topics_forecast_{category}_{today_str}_{unique_id}.png'
    
    static_folder = os.path.join(current_app.root_path, 'static', 'images')
    os.makedirs(static_folder, exist_ok=True)
    
    filepath = os.path.join(static_folder, filename)
    plt.savefig(filepath, dpi=100, bbox_inches='tight')
    plt.close()
    
    return f'/static/images/{filename}'

# Р’СЃРїРѕРјРѕРіР°С‚РµР»СЊРЅР°СЏ С„СѓРЅРєС†РёСЏ РґР»СЏ РїРѕР»СѓС‡РµРЅРёСЏ С‡РёС‚Р°РµРјРѕРіРѕ РЅР°Р·РІР°РЅРёСЏ РєР°С‚РµРіРѕСЂРёРё
def get_category_name(category):
    categories = {
        'all': 'Все категории',
        'military_operations': 'Военные операции',
        'humanitarian_crisis': 'Гуманитарный кризис',
        'economic_consequences': 'Экономические последствия',
        'political_decisions': 'Политические решения',
        'information_social': 'Информационно-социальные аспекты'
    }
    return categories.get(category, category)
