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

# Создаем простые классы-обертки для функциональных парсеров
class ParserWrapper:
    """Обертка для функциональных парсеров"""
    def __init__(self, parser_func, name):
        self.parser_func = parser_func
        self.name = name
        self.source_name = name
    
    def run(self):
        return self.parser_func()
    
    def get_articles(self):
        """Возвращает тестовые статьи для демонстрации"""
        return [
            {
                'title': f'Тестовая новость от {self.name}',
                'content': f'Это тестовое содержимое новости от источника {self.name}. Новость содержит подробную информацию о текущих событиях в мире. Данная статья демонстрирует работу системы парсинга новостей с AI-классификатором. Содержимое статьи достаточно длинное для прохождения валидации контента и содержит различные аспекты освещаемых событий.',
                'link': f'https://example.com/{self.name.lower().replace(" ", "-")}/test-article',
                'published_date': '2024-01-01 12:00:00'
            },
            {
                'title': f'Вторая тестовая новость от {self.name}',
                'content': f'Еще одна тестовая новость от {self.name} для демонстрации работы системы. Данная статья также содержит достаточно информации для прохождения всех этапов обработки, включая валидацию контента, AI-классификацию и расчет индексов напряженности. Система должна корректно обработать эту новость и сохранить результаты в базе данных.',
                'link': f'https://example.com/{self.name.lower().replace(" ", "-")}/test-article-2',
                'published_date': '2024-01-01 13:00:00'
            }
        ]

# Функция-заглушка для тестирования
def dummy_parser():
    """Заглушка парсера для тестирования"""
    import time
    time.sleep(1)  # Имитируем работу парсера
    print(f"Заглушка парсера выполнена")

# Создаем классы парсеров с заглушками
class RiaParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'РИА Новости')

class LentaParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'Lenta.ru')

class RbcParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'RBC.ru')

class GazetaParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'Gazeta.ru')

class KommersantParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'Kommersant.ru')

class TsnParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'TSN.ua')

class UnianParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'UNIAN.ua')

class RtParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'RT.com')

class IsrailParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, '7kanal.co.il')

class TelegramParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'Telegram каналы')

class CnnParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'CNN')

class AljazeeraParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'Al Jazeera')

class ReutersParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'Reuters')

class France24Parser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'France 24')

class DwParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'Deutsche Welle')

class EuronewsParser(ParserWrapper):
    def __init__(self):
        super().__init__(dummy_parser, 'Euronews')

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
            'ria': {'class': RiaParser, 'name': 'РИА Новости', 'status': 'ready'},
            'lenta': {'class': LentaParser, 'name': 'Lenta.ru', 'status': 'ready'},
            'rbc': {'class': RbcParser, 'name': 'RBC.ru', 'status': 'ready'},
            'gazeta': {'class': GazetaParser, 'name': 'Gazeta.ru', 'status': 'ready'},
            'kommersant': {'class': KommersantParser, 'name': 'Kommersant.ru', 'status': 'ready'},
            'tsn': {'class': TsnParser, 'name': 'TSN.ua', 'status': 'ready'},
            'unian': {'class': UnianParser, 'name': 'UNIAN.ua', 'status': 'ready'},
            'rt': {'class': RtParser, 'name': 'RT.com', 'status': 'ready'},
            'israil': {'class': IsrailParser, 'name': '7kanal.co.il', 'status': 'ready'},
            'telegram': {'class': TelegramParser, 'name': 'Telegram каналы', 'status': 'ready'},
            'cnn': {'class': CnnParser, 'name': 'CNN', 'status': 'ready'},
            'aljazeera': {'class': AljazeeraParser, 'name': 'Al Jazeera', 'status': 'ready'},
            'reuters': {'class': ReutersParser, 'name': 'Reuters', 'status': 'ready'},
            'france24': {'class': France24Parser, 'name': 'France 24', 'status': 'ready'},
            'dw': {'class': DwParser, 'name': 'Deutsche Welle', 'status': 'ready'},
            'euronews': {'class': EuronewsParser, 'name': 'Euronews', 'status': 'ready'}
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
            
            # Создаем экземпляр парсера и запускаем
            parser_class = parser_info['class']
            parser_instance = parser_class()
            parser_instance.run()
            
            self.parsers[parser_key]['status'] = 'completed'
            logger.info(f"Парсер {parser_info['name']} завершен успешно")
            return True
            
        except Exception as e:
            self.parsers[parser_key]['status'] = 'failed'
            logger.error(f"Ошибка в парсере {parser_info['name']}: {e}")
            return False
    
    def run_parser_safe(self, parser_key):
        """Безопасный запуск отдельного парсера с изоляцией ошибок"""
        parser_info = self.parsers.get(parser_key)
        if not parser_info:
            logger.error(f"Парсер {parser_key} не найден")
            return {'parser': parser_key, 'status': 'error', 'error': 'Parser not found'}
        
        try:
            logger.info(f"Запуск парсера: {parser_info['name']}")
            self.parsers[parser_key]['status'] = 'running'
            
            # Создаем экземпляр парсера и запускаем
            start_time = time.time()
            parser_class = parser_info['class']
            parser_instance = parser_class()
            parser_instance.run()
            end_time = time.time()
            
            self.parsers[parser_key]['status'] = 'completed'
            logger.info(f"Парсер {parser_info['name']} завершен успешно за {end_time - start_time:.2f} сек")
            
            return {
                'parser': parser_key,
                'status': 'success',
                'duration': end_time - start_time,
                'name': parser_info['name']
            }
            
        except Exception as e:
            self.parsers[parser_key]['status'] = 'error'
            error_msg = str(e)
            logger.error(f"Парсер {parser_info['name']} завершился с ошибкой: {error_msg}")
            
            return {
                'parser': parser_key,
                'status': 'error',
                'error': error_msg,
                'name': parser_info['name']
            }
    
    def run_all_parsers(self, max_workers=4):
        """Запуск всех парсеров параллельно с изоляцией ошибок"""
        logger.info("Запуск всех парсеров")
        self.stats['total_runs'] += 1
        self.stats['last_run'] = datetime.now()
        
        successful = 0
        failed = 0
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Запуск всех парсеров с безопасной обработкой ошибок
            future_to_parser = {
                executor.submit(self.run_parser_safe, parser_key): parser_key 
                for parser_key in self.parsers.keys()
            }
            
            # Обработка результатов по мере готовности
            for future in as_completed(future_to_parser):
                parser_key = future_to_parser[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['status'] == 'success':
                        successful += 1
                        logger.info(f"✅ {result['name']}: успешно ({result['duration']:.2f}с)")
                    else:
                        failed += 1
                        logger.error(f"❌ {result['name']}: ошибка - {result['error']}")
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"❌ Исключение в парсере {parser_key}: {e}")
                    results.append({
                        'parser': parser_key,
                        'status': 'error',
                        'error': str(e),
                        'name': self.parsers[parser_key]['name']
                    })
        
        # Обновляем статистику
        self.stats['successful_runs'] += successful
        self.stats['failed_runs'] += failed
        
        logger.info(f"Парсинг завершен: {successful} успешно, {failed} с ошибками")
        
        return {
            'successful': successful,
            'failed': failed,
            'total': successful + failed,
            'results': results,
            'stats': self.stats
        }
    
    def run_all_parsers_with_callback(self, max_workers=4, callback=None):
        """Запуск всех парсеров с callback для немедленного отображения результатов"""
        logger.info("Запуск всех парсеров с callback")
        self.stats['total_runs'] += 1
        self.stats['last_run'] = datetime.now()
        
        successful = 0
        failed = 0
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Запуск всех парсеров с безопасной обработкой ошибок
            future_to_parser = {
                executor.submit(self.run_parser_safe, parser_key): parser_key 
                for parser_key in self.parsers.keys()
            }
            
            # Обработка результатов по мере готовности
            for future in as_completed(future_to_parser):
                parser_key = future_to_parser[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result['status'] == 'success':
                        successful += 1
                        logger.info(f"✅ {result['name']}: успешно ({result['duration']:.2f}с)")
                    else:
                        failed += 1
                        logger.error(f"❌ {result['name']}: ошибка - {result['error']}")
                    
                    # Вызываем callback для немедленного отображения результата
                    if callback:
                        callback(result)
                        
                except Exception as e:
                    failed += 1
                    logger.error(f"❌ Исключение в парсере {parser_key}: {e}")
                    error_result = {
                        'parser': parser_key,
                        'status': 'error',
                        'error': str(e),
                        'name': self.parsers[parser_key]['name']
                    }
                    results.append(error_result)
                    
                    if callback:
                        callback(error_result)
        
        # Обновляем статистику
        self.stats['successful_runs'] += successful
        self.stats['failed_runs'] += failed
        
        logger.info(f"Парсинг завершен: {successful} успешно, {failed} с ошибками")
        
        return {
            'successful': successful,
            'failed': failed,
            'total': successful + failed,
            'results': results,
            'stats': self.stats
        }
    
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
