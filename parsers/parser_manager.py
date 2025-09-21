#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер парсеров новостей

Этот модуль содержит функции для:
- Управления всеми парсерами новостей
- Запуска парсеров по расписанию
- Мониторинга работы парсеров
- Сбора статистики парсинга
"""

import sys
import os
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорт всех парсеров
try:
    from parser_ria import main as parse_ria
    from parser_lenta import main as parse_lenta
    from parser_rbc import main as parse_rbc
    from parser_gazeta import main as parse_gazeta
    from parser_kommersant import main as parse_kommersant
    from parser_tsn import main as parse_tsn
    from parser_unian import main as parse_unian
    from parser_rt import main as parse_rt
    from parser_israil import main as parse_israil
    from parser_telegram import main as parse_telegram
    from parser_cnn import main as parse_cnn
    from parser_aljazeera import main as parse_aljazeera
    from parser_reuters import main as parse_reuters
    from parser_france24 import main as parse_france24
    from parser_dw import main as parse_dw
    from parser_euronews import main as parse_euronews
except ImportError as e:
    print(f"Ошибка импорта парсеров: {e}")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("parser_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ParserManager:
    """Менеджер для управления всеми парсерами новостей"""
    
    def __init__(self):
        self.parsers = {
            'ria': {'func': parse_ria, 'name': 'РИА Новости', 'status': 'ready'},
            'lenta': {'func': parse_lenta, 'name': 'Lenta.ru', 'status': 'ready'},
            'rbc': {'func': parse_rbc, 'name': 'RBC.ru', 'status': 'ready'},
            'gazeta': {'func': parse_gazeta, 'name': 'Gazeta.ru', 'status': 'ready'},
            'kommersant': {'func': parse_kommersant, 'name': 'Kommersant.ru', 'status': 'ready'},
            'tsn': {'func': parse_tsn, 'name': 'TSN.ua', 'status': 'ready'},
            'unian': {'func': parse_unian, 'name': 'UNIAN.ua', 'status': 'ready'},
            'rt': {'func': parse_rt, 'name': 'RT.com', 'status': 'ready'},
            'israil': {'func': parse_israil, 'name': '7kanal.co.il', 'status': 'ready'},
            'telegram': {'func': parse_telegram, 'name': 'Telegram каналы', 'status': 'ready'},
            'cnn': {'func': parse_cnn, 'name': 'CNN', 'status': 'ready'},
            'aljazeera': {'func': parse_aljazeera, 'name': 'Al Jazeera', 'status': 'ready'},
            'reuters': {'func': parse_reuters, 'name': 'Reuters', 'status': 'ready'},
            'france24': {'func': parse_france24, 'name': 'France 24', 'status': 'ready'},
            'dw': {'func': parse_dw, 'name': 'Deutsche Welle', 'status': 'ready'},
            'euronews': {'func': parse_euronews, 'name': 'Euronews', 'status': 'ready'}
        }
        self.stats = {
            'total_runs': 0,
            'successful_runs': 0,
            'failed_runs': 0,
            'last_run': None
        }
    
    def run_parser(self, parser_key):
        """Запуск отдельного парсера"""
        parser_info = self.parsers.get(parser_key)
        if not parser_info:
            logger.error(f"Парсер {parser_key} не найден")
            return False
        
        try:
            logger.info(f"Запуск парсера: {parser_info['name']}")
            self.parsers[parser_key]['status'] = 'running'
            
            # Запуск парсера
            parser_info['func']()
            
            self.parsers[parser_key]['status'] = 'completed'
            logger.info(f"Парсер {parser_info['name']} завершен успешно")
            return True
            
        except Exception as e:
            self.parsers[parser_key]['status'] = 'failed'
            logger.error(f"Ошибка в парсере {parser_info['name']}: {e}")
            return False
    
    def run_all_parsers(self, max_workers=4):
        """Запуск всех парсеров параллельно"""
        logger.info("Запуск всех парсеров")
        self.stats['total_runs'] += 1
        self.stats['last_run'] = datetime.now()
        
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Запуск всех парсеров
            future_to_parser = {
                executor.submit(self.run_parser, parser_key): parser_key 
                for parser_key in self.parsers.keys()
            }
            
            # Ожидание завершения
            for future in as_completed(future_to_parser):
                parser_key = future_to_parser[future]
                try:
                    result = future.result()
                    if result:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Исключение в парсере {parser_key}: {e}")
                    failed += 1
        
        self.stats['successful_runs'] += successful
        self.stats['failed_runs'] += failed
        
        logger.info(f"Парсинг завершен. Успешно: {successful}, Ошибок: {failed}")
        return successful, failed
    
    def run_selected_parsers(self, parser_keys, max_workers=4):
        """Запуск выбранных парсеров"""
        logger.info(f"Запуск выбранных парсеров: {', '.join(parser_keys)}")
        
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_parser = {
                executor.submit(self.run_parser, parser_key): parser_key 
                for parser_key in parser_keys if parser_key in self.parsers
            }
            
            for future in as_completed(future_to_parser):
                parser_key = future_to_parser[future]
                try:
                    result = future.result()
                    if result:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Исключение в парсере {parser_key}: {e}")
                    failed += 1
        
        logger.info(f"Выборочный парсинг завершен. Успешно: {successful}, Ошибок: {failed}")
        return successful, failed
    
    def get_status(self):
        """Получение статуса всех парсеров"""
        status_info = {
            'parsers': self.parsers.copy(),
            'stats': self.stats.copy()
        }
        return status_info
    
    def print_status(self):
        """Вывод статуса парсеров"""
        print("\n=== СТАТУС ПАРСЕРОВ ===")
        for key, info in self.parsers.items():
            print(f"{info['name']}: {info['status']}")
        
        print("\n=== СТАТИСТИКА ===")
        print(f"Всего запусков: {self.stats['total_runs']}")
        print(f"Успешных: {self.stats['successful_runs']}")
        print(f"Неудачных: {self.stats['failed_runs']}")
        if self.stats['last_run']:
            print(f"Последний запуск: {self.stats['last_run']}")

def main():
    """Главная функция для запуска менеджера парсеров"""
    manager = ParserManager()
    
    # Проверка аргументов командной строки
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'all':
            # Запуск всех парсеров
            manager.run_all_parsers()
        elif command == 'status':
            # Показать статус
            manager.print_status()
        elif command in manager.parsers:
            # Запуск конкретного парсера
            manager.run_parser(command)
        elif command == 'russian':
            # Запуск только российских источников
            russian_parsers = ['ria', 'lenta', 'rbc', 'gazeta', 'kommersant']
            manager.run_selected_parsers(russian_parsers)
        elif command == 'ukrainian':
            # Запуск только украинских источников
            ukrainian_parsers = ['tsn', 'unian']
            manager.run_selected_parsers(ukrainian_parsers)
        elif command == 'international':
            # Запуск международных источников
            international_parsers = ['rt', 'israil', 'telegram', 'cnn', 'aljazeera', 'reuters', 'france24', 'dw', 'euronews']
            manager.run_selected_parsers(international_parsers)
        else:
            print(f"Неизвестная команда: {command}")
            print("Доступные команды:")
            print("  all - запустить все парсеры")
            print("  status - показать статус")
            print("  russian - российские источники")
            print("  ukrainian - украинские источники")
            print("  international - международные источники")
            print("  Или название конкретного парсера:", ', '.join(manager.parsers.keys()))
    else:
        # По умолчанию запускаем все парсеры
        manager.run_all_parsers()
    
    # Показать финальный статус
    manager.print_status()

if __name__ == "__main__":
    main()
