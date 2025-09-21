#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import time

def test_api_endpoint(url, description):
    """Тестирует API эндпоинт"""
    print(f"\n🔍 Тестирую: {description}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Успешно получены данные")
                
                # Проверяем структуру данных
                if isinstance(data, dict):
                    print(f"📊 Ключи в ответе: {list(data.keys())}")
                    
                    # Проверяем наличие данных
                    if 'data' in data:
                        print(f"📈 Количество записей: {len(data['data']) if isinstance(data['data'], list) else 'N/A'}")
                    elif 'categories' in data:
                        print(f"📈 Количество категорий: {len(data['categories']) if isinstance(data['categories'], list) else 'N/A'}")
                    elif 'labels' in data and 'datasets' in data:
                        print(f"📈 График: {len(data['labels'])} меток, {len(data['datasets'])} наборов данных")
                    
                elif isinstance(data, list):
                    print(f"📈 Количество элементов: {len(data)}")
                    
                return True
                
            except json.JSONDecodeError:
                print(f"❌ Ошибка декодирования JSON")
                print(f"Ответ: {response.text[:200]}...")
                return False
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            print(f"Ответ: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return False

def main():
    base_url = "http://127.0.0.1:5000"
    
    print("🚀 Тестирование API эндпоинтов графиков и статистики")
    print("=" * 60)
    
    # Список эндпоинтов для тестирования
    endpoints = [
        # Основные статистические эндпоинты
        ("/api/database/statistics", "Статистика базы данных"),
        ("/api/news/statistics", "Статистика новостей"),
        
        # Графики и аналитика
        ("/api/charts/category-distribution", "Распределение по категориям"),
        ("/api/charts/timeline", "Временная линия"),
        ("/api/charts/source-distribution", "Распределение по источникам"),
        ("/api/charts/sentiment-analysis", "Анализ настроений"),
        
        # Украинская аналитика
        ("/api/ukraine/analytics/timeline", "Временная линия Украины"),
        ("/api/ukraine/analytics/categories", "Категории Украины"),
        ("/api/ukraine/analytics/sentiment", "Настроения Украины"),
        
        # Прогнозы
        ("/api/forecast/ukraine-conflict", "Прогноз конфликта"),
        ("/api/forecast/categories", "Прогноз категорий"),
        
        # Социальная аналитика
        ("/api/social/tension-analysis", "Анализ социальной напряженности"),
        ("/api/social/extremism-detection", "Детекция экстремизма"),
    ]
    
    successful_tests = 0
    total_tests = len(endpoints)
    
    for endpoint, description in endpoints:
        url = base_url + endpoint
        if test_api_endpoint(url, description):
            successful_tests += 1
        time.sleep(0.5)  # Небольшая пауза между запросами
    
    print("\n" + "=" * 60)
    print(f"📊 Результаты тестирования:")
    print(f"✅ Успешных тестов: {successful_tests}/{total_tests}")
    print(f"❌ Неудачных тестов: {total_tests - successful_tests}/{total_tests}")
    
    if successful_tests == total_tests:
        print("🎉 Все тесты прошли успешно!")
    elif successful_tests > total_tests * 0.8:
        print("⚠️ Большинство тестов прошли успешно, но есть проблемы")
    else:
        print("🚨 Много ошибок в API эндпоинтах")

if __name__ == "__main__":
    main()