#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time

def test_endpoint(url, description):
    """Тестирует эндпоинт"""
    print(f"\n🔍 Тестирую: {description}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Статус: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Успешно")
            return True
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка запроса: {e}")
        return False

def main():
    base_url = "http://127.0.0.1:5000"
    
    print("🚀 Тестирование основных эндпоинтов")
    print("=" * 50)
    
    # Основные страницы
    pages = [
        ("/", "Главная страница"),
        ("/analytics", "Аналитика"),
        ("/clickhouse", "База данных"),
        ("/predict", "Прогнозы"),
        ("/about", "О проекте"),
    ]
    
    # API эндпоинты
    api_endpoints = [
        ("/api/news", "API новостей"),
        ("/api/news/statistics", "Статистика новостей"),
    ]
    
    successful_tests = 0
    total_tests = len(pages) + len(api_endpoints)
    
    print("\n📄 Тестирование страниц:")
    for endpoint, description in pages:
        url = base_url + endpoint
        if test_endpoint(url, description):
            successful_tests += 1
        time.sleep(0.3)
    
    print("\n🔌 Тестирование API:")
    for endpoint, description in api_endpoints:
        url = base_url + endpoint
        if test_endpoint(url, description):
            successful_tests += 1
        time.sleep(0.3)
    
    print("\n" + "=" * 50)
    print(f"📊 Результаты: {successful_tests}/{total_tests} успешных тестов")
    
    if successful_tests == total_tests:
        print("🎉 Все тесты прошли успешно!")
    elif successful_tests > 0:
        print("⚠️ Частично работает")
    else:
        print("🚨 Ничего не работает")

if __name__ == "__main__":
    main()