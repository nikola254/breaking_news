#!/usr/bin/env python3
"""
Скрипт для последовательного запуска всех парсеров
Наполняет базу данных новыми статьями с Gen-API классификатором
"""

import sys
import os
import time
import logging
from datetime import datetime

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parsers_batch_run.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_parser(parser_function, parser_name, max_articles=10):
    """Запуск одного парсера"""
    print(f"\n{'='*60}")
    print(f"🚀 Запуск парсера: {parser_name}")
    print(f"{'='*60}")
    
    try:
        # Запускаем функцию парсера
        start_time = time.time()
        articles_count = parser_function()
        end_time = time.time()
        
        duration = end_time - start_time
        
        print(f"✅ {parser_name}: обработано {articles_count} статей за {duration:.1f} сек")
        logger.info(f"{parser_name}: обработано {articles_count} статей за {duration:.1f} сек")
        
        return articles_count
        
    except Exception as e:
        print(f"❌ {parser_name}: ошибка - {e}")
        logger.error(f"{parser_name}: ошибка - {e}")
        return 0

def run_all_parsers():
    """Запуск всех парсеров последовательно"""
    print("🚀 ЗАПУСК ВСЕХ ПАРСЕРОВ С GEN-API КЛАССИФИКАТОРОМ")
    print("=" * 80)
    
    # Список всех парсеров (функции, а не классы)
    parsers = [
        # Российские источники
        ("parsers.parser_lenta", "parse_lenta_news", "Lenta.ru"),
        ("parsers.parser_gazeta", "parse_gazeta_news", "Gazeta.ru"),
        ("parsers.parser_rbc", "parse_rbc_news", "RBC"),
        ("parsers.parser_kommersant", "parse_kommersant_news", "Kommersant"),
        ("parsers.parser_rt", "parse_rt_news", "RT"),
        ("parsers.parser_dw", "parse_dw_news", "Deutsche Welle"),
        
        # Международные источники
        ("parsers.parser_cnn", "parse_cnn_news", "CNN"),
        ("parsers.parser_bbc", "parse_bbc_news", "BBC"),
        ("parsers.parser_reuters", "parse_reuters_news", "Reuters"),
        ("parsers.parser_euronews", "parse_euronews_news", "Euronews"),
        ("parsers.parser_france24", "parse_france24_news", "France24"),
        ("parsers.parser_aljazeera", "parse_aljazeera_news", "Al Jazeera"),
        
        # Украинские источники
        ("parsers.parser_unian", "parse_unian_news", "Unian"),
        ("parsers.parser_tsn", "parse_tsn_news", "TSN"),
        
        # Социальные сети
        ("parsers.parser_telegram", "parse_telegram_news", "Telegram"),
        ("parsers.parser_twitter", "parse_twitter_news", "Twitter"),
    ]
    
    total_articles = 0
    successful_parsers = 0
    failed_parsers = 0
    
    start_time = time.time()
    
    for module_name, function_name, display_name in parsers:
        try:
            # Импортируем модуль и функцию
            module = __import__(module_name, fromlist=[function_name])
            parser_function = getattr(module, function_name)
            
            # Запускаем парсер
            articles_count = run_parser(parser_function, display_name, max_articles=5)
            
            if articles_count > 0:
                successful_parsers += 1
                total_articles += articles_count
            else:
                failed_parsers += 1
            
            # Небольшая пауза между парсерами
            time.sleep(2)
            
        except ImportError as e:
            print(f"❌ {display_name}: модуль не найден - {e}")
            logger.error(f"{display_name}: модуль не найден - {e}")
            failed_parsers += 1
        except Exception as e:
            print(f"❌ {display_name}: ошибка импорта - {e}")
            logger.error(f"{display_name}: ошибка импорта - {e}")
            failed_parsers += 1
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Итоговая статистика
    print(f"\n{'='*80}")
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*80}")
    print(f"✅ Успешных парсеров: {successful_parsers}")
    print(f"❌ Неудачных парсеров: {failed_parsers}")
    print(f"📰 Всего статей: {total_articles}")
    print(f"⏱️ Общее время: {total_duration:.1f} сек")
    print(f"📈 Средняя скорость: {total_articles/total_duration:.1f} статей/сек")
    
    logger.info(f"ИТОГО: {successful_parsers} успешных, {failed_parsers} неудачных, {total_articles} статей за {total_duration:.1f} сек")

if __name__ == "__main__":
    print(f"🕐 Начало работы: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        run_all_parsers()
        print(f"\n🎉 Все парсеры завершены: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    except KeyboardInterrupt:
        print("\n⚠️ Работа прервана пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}")
