#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Миграция базы данных для добавления полей AI-классификации и индексов напряженности

Этот скрипт добавляет следующие поля ко всем таблицам новостей:
- social_tension_index: Float32 - индекс социальной напряженности (0-100)
- spike_index: Float32 - индекс всплеска/срочности (0-100)
- ai_classification_metadata: String - метаданные AI-классификации (JSON)
- ai_category: String - категория от AI-классификатора
- ai_confidence: Float32 - уверенность AI в классификации (0-1)
- content_validated: UInt8 - флаг валидации контента (0/1)
"""

import os
import sys
import logging
from clickhouse_driver import Client
from datetime import datetime

# Добавляем корневую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config

CLICKHOUSE_CONFIG = Config.CLICKHOUSE_CONFIG

logger = logging.getLogger(__name__)

class DatabaseMigration:
    """Класс для выполнения миграций базы данных"""
    
    def __init__(self):
        self.client = Client(
            host=CLICKHOUSE_CONFIG['host'],
            port=CLICKHOUSE_CONFIG['port'],
            user=CLICKHOUSE_CONFIG['user'],
            password=CLICKHOUSE_CONFIG['password'],
            database=CLICKHOUSE_CONFIG['database']
        )
        
        # Список всех таблиц новостей для миграции
        self.news_tables = [
            'ria_headlines',
            'lenta_headlines', 
            'rbc_headlines',
            'gazeta_headlines',
            'kommersant_headlines',
            'telegram_headlines',
            'bbc_headlines',
            'cnn_headlines',
            'dw_headlines',
            'euronews_headlines',
            'france24_headlines',
            'reuters_headlines',
            'rt_headlines',
            'tsn_headlines',
            'unian_headlines',
            'israil_headlines',
            'aljazeera_headlines'
        ]
        
        # Дополнительные таблицы по категориям
        self.category_tables = [
            'military_operations',
            'humanitarian_crisis',
            'economic_consequences', 
            'political_decisions',
            'information_social'
        ]
    
    def check_table_exists(self, table_name: str) -> bool:
        """
        Проверяет существование таблицы
        
        Args:
            table_name: Имя таблицы
            
        Returns:
            bool: True если таблица существует
        """
        try:
            query = f"EXISTS TABLE news.{table_name}"
            result = self.client.execute(query)
            return result[0][0] if result else False
        except Exception as e:
            logger.error(f"Ошибка при проверке существования таблицы {table_name}: {e}")
            return False
    
    def get_table_columns(self, table_name: str) -> list:
        """
        Получает список колонок таблицы
        
        Args:
            table_name: Имя таблицы
            
        Returns:
            list: Список колонок
        """
        try:
            query = f"DESCRIBE TABLE news.{table_name}"
            result = self.client.execute(query)
            return [row[0] for row in result] if result else []
        except Exception as e:
            logger.error(f"Ошибка при получении колонок таблицы {table_name}: {e}")
            return []
    
    def add_column_if_not_exists(self, table_name: str, column_name: str, column_type: str, default_value: str = None):
        """
        Добавляет колонку в таблицу если она не существует
        
        Args:
            table_name: Имя таблицы
            column_name: Имя колонки
            column_type: Тип колонки
            default_value: Значение по умолчанию
        """
        try:
            # Проверяем существование колонки
            columns = self.get_table_columns(table_name)
            if column_name in columns:
                logger.info(f"Колонка {column_name} уже существует в таблице {table_name}")
                return True
            
            # Формируем SQL для добавления колонки
            if default_value is not None:
                sql = f"ALTER TABLE news.{table_name} ADD COLUMN {column_name} {column_type} DEFAULT {default_value}"
            else:
                sql = f"ALTER TABLE news.{table_name} ADD COLUMN {column_name} {column_type}"
            
            logger.info(f"Добавляем колонку {column_name} в таблицу {table_name}")
            self.client.execute(sql)
            logger.info(f"✅ Колонка {column_name} успешно добавлена в таблицу {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении колонки {column_name} в таблицу {table_name}: {e}")
            return False
    
    def migrate_table(self, table_name: str) -> bool:
        """
        Мигрирует одну таблицу
        
        Args:
            table_name: Имя таблицы
            
        Returns:
            bool: True если миграция успешна
        """
        logger.info(f"Начинаем миграцию таблицы: {table_name}")
        
        # Проверяем существование таблицы
        if not self.check_table_exists(table_name):
            logger.warning(f"Таблица {table_name} не существует, пропускаем")
            return True
        
        success = True
        
        # Добавляем новые колонки
        columns_to_add = [
            ('social_tension_index', 'Float32', '0.0'),
            ('spike_index', 'Float32', '0.0'),
            ('ai_classification_metadata', 'String', "''"),
            ('ai_category', 'String', "''"),
            ('ai_confidence', 'Float32', '0.0'),
            ('content_validated', 'UInt8', '0')
        ]
        
        for column_name, column_type, default_value in columns_to_add:
            if not self.add_column_if_not_exists(table_name, column_name, column_type, default_value):
                success = False
        
        if success:
            logger.info(f"✅ Миграция таблицы {table_name} завершена успешно")
        else:
            logger.error(f"❌ Миграция таблицы {table_name} завершена с ошибками")
        
        return success
    
    def migrate_all_tables(self) -> bool:
        """
        Мигрирует все таблицы новостей
        
        Returns:
            bool: True если все миграции успешны
        """
        logger.info("Начинаем миграцию всех таблиц новостей")
        start_time = datetime.now()
        
        success_count = 0
        total_count = 0
        
        # Мигрируем основные таблицы новостей
        for table_name in self.news_tables:
            total_count += 1
            if self.migrate_table(table_name):
                success_count += 1
        
        # Мигрируем таблицы по категориям
        for table_name in self.category_tables:
            total_count += 1
            if self.migrate_table(table_name):
                success_count += 1
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Миграция завершена: {success_count}/{total_count} таблиц успешно")
        logger.info(f"Время выполнения: {duration:.2f} секунд")
        
        return success_count == total_count
    
    def verify_migration(self) -> bool:
        """
        Проверяет успешность миграции
        
        Returns:
            bool: True если миграция прошла успешно
        """
        logger.info("Проверяем результаты миграции")
        
        required_columns = [
            'social_tension_index',
            'spike_index', 
            'ai_classification_metadata',
            'ai_category',
            'ai_confidence',
            'content_validated'
        ]
        
        all_tables_ok = True
        
        for table_name in self.news_tables + self.category_tables:
            if not self.check_table_exists(table_name):
                continue
                
            columns = self.get_table_columns(table_name)
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                logger.error(f"❌ В таблице {table_name} отсутствуют колонки: {missing_columns}")
                all_tables_ok = False
            else:
                logger.info(f"✅ Таблица {table_name} содержит все необходимые колонки")
        
        return all_tables_ok
    
    def create_indexes(self):
        """
        Создает индексы для новых полей (если поддерживается ClickHouse)
        """
        logger.info("Создаем индексы для новых полей")
        
        # ClickHouse поддерживает индексы только для некоторых типов данных
        # Для Float32 и String полей индексы не создаются автоматически
        logger.info("Индексы для новых полей не требуются в ClickHouse")
    
    def rollback_migration(self):
        """
        Откатывает миграцию (удаляет добавленные колонки)
        ВНИМАНИЕ: Это удалит все данные в новых колонках!
        """
        logger.warning("ВНИМАНИЕ: Выполняется откат миграции!")
        logger.warning("Это удалит все данные в новых колонках!")
        
        confirm = input("Вы уверены? Введите 'yes' для подтверждения: ")
        if confirm.lower() != 'yes':
            logger.info("Откат отменен")
            return
        
        columns_to_remove = [
            'social_tension_index',
            'spike_index',
            'ai_classification_metadata', 
            'ai_category',
            'ai_confidence',
            'content_validated'
        ]
        
        for table_name in self.news_tables + self.category_tables:
            if not self.check_table_exists(table_name):
                continue
                
            for column_name in columns_to_remove:
                try:
                    sql = f"ALTER TABLE news.{table_name} DROP COLUMN {column_name}"
                    self.client.execute(sql)
                    logger.info(f"✅ Колонка {column_name} удалена из таблицы {table_name}")
                except Exception as e:
                    logger.error(f"❌ Ошибка при удалении колонки {column_name} из таблицы {table_name}: {e}")


def main():
    """Основная функция для выполнения миграции"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Запуск миграции базы данных для AI-классификации")
    
    try:
        migration = DatabaseMigration()
        
        # Выполняем миграцию
        if migration.migrate_all_tables():
            logger.info("✅ Миграция всех таблиц завершена успешно")
            
            # Проверяем результаты
            if migration.verify_migration():
                logger.info("✅ Проверка миграции прошла успешно")
                logger.info("🎉 Миграция базы данных завершена!")
            else:
                logger.error("❌ Проверка миграции выявила проблемы")
                return False
        else:
            logger.error("❌ Миграция завершена с ошибками")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при выполнении миграции: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Миграция базы данных для AI-классификации')
    parser.add_argument('--rollback', action='store_true', help='Откатить миграцию')
    parser.add_argument('--verify', action='store_true', help='Только проверить состояние миграции')
    
    args = parser.parse_args()
    
    if args.rollback:
        migration = DatabaseMigration()
        migration.rollback_migration()
    elif args.verify:
        migration = DatabaseMigration()
        if migration.verify_migration():
            print("✅ Миграция выполнена корректно")
        else:
            print("❌ Миграция выполнена некорректно")
    else:
        success = main()
        sys.exit(0 if success else 1)
