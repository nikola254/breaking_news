#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

def test_api_statistics():
    # Тестируем API статистики
    try:
        response = requests.get('http://localhost:5000/api/news/statistics', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print('Статистика из API /api/news/statistics:')
            print('Всего статей:', data['data']['total'])
            print()
            print('По категориям:')
            for key, category in data['data']['categories'].items():
                print(f'{category["count"]}: {category["name"]}')
        else:
            print('Ошибка HTTP:', response.status_code)
            print(response.text)
    except Exception as e:
        print('Ошибка:', e)

if __name__ == '__main__':
    test_api_statistics()
