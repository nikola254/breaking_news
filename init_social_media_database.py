#!/usr/bin/env python3
"""
Скрипт для создания таблиц социальных сетей в ClickHouse
Создает таблицы для хранения данных из Twitter, VK, OK
"""

import clickhouse_connect
from config import Config
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_clickhouse_client():
    """Создание клиента ClickHouse"""
    if Config.CLICKHOUSE_PASSWORD:
        return clickhouse_connect.get_client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_PORT,
            username=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD
        )
    else:
        return clickhouse_connect.get_client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_PORT,
            username=Config.CLICKHOUSE_USER
        )

def create_social_media_database():
    """Создание базы данных для социальных сетей"""
    client = get_clickhouse_client()
    
    try:
        # Создаем базу данных для социальных сетей
        client.command("CREATE DATABASE IF NOT EXISTS social_media")
        logger.info("База данных social_media создана")
        
        # Таблица для постов Twitter
        twitter_posts_sql = """
        CREATE TABLE IF NOT EXISTS social_media.twitter_posts (
            id String,
            text String,
            author_id String,
            author_username String,
            author_name String,
            created_at DateTime,
            public_metrics_retweet_count UInt32,
            public_metrics_like_count UInt32,
            public_metrics_reply_count UInt32,
            public_metrics_quote_count UInt32,
            lang String,
            possibly_sensitive UInt8,
            context_annotations Array(String),
            hashtags Array(String),
            mentions Array(String),
            urls Array(String),
            extremism_percentage Float32,
            risk_level String,
            analysis_method String,
            keywords_matched Array(String),
            parsed_date DateTime DEFAULT now(),
            source String DEFAULT 'twitter'
        ) ENGINE = MergeTree()
        ORDER BY (created_at, id)
        PARTITION BY toYYYYMM(created_at)
        """
        
        # Таблица для постов VKontakte
        vk_posts_sql = """
        CREATE TABLE IF NOT EXISTS social_media.vk_posts (
            id String,
            owner_id String,
            from_id String,
            text String,
            date DateTime,
            post_type String,
            attachments Array(String),
            comments_count UInt32,
            likes_count UInt32,
            reposts_count UInt32,
            views_count UInt32,
            is_pinned UInt8,
            marked_as_ads UInt8,
            geo_place String,
            signer_id String,
            copy_history Array(String),
            extremism_percentage Float32,
            risk_level String,
            analysis_method String,
            keywords_matched Array(String),
            parsed_date DateTime DEFAULT now(),
            source String DEFAULT 'vk'
        ) ENGINE = MergeTree()
        ORDER BY (date, id)
        PARTITION BY toYYYYMM(date)
        """
        
        # Таблица для постов Одноклассники
        ok_posts_sql = """
        CREATE TABLE IF NOT EXISTS social_media.ok_posts (
            id String,
            author_id String,
            author_name String,
            text String,
            created_time DateTime,
            media Array(String),
            likes_count UInt32,
            comments_count UInt32,
            reshares_count UInt32,
            group_id String,
            group_name String,
            post_type String,
            link_url String,
            link_title String,
            extremism_percentage Float32,
            risk_level String,
            analysis_method String,
            keywords_matched Array(String),
            parsed_date DateTime DEFAULT now(),
            source String DEFAULT 'ok'
        ) ENGINE = MergeTree()
        ORDER BY (created_time, id)
        PARTITION BY toYYYYMM(created_time)
        """
        
        # Таблица для Telegram постов (уже может существовать)
        telegram_posts_sql = """
        CREATE TABLE IF NOT EXISTS social_media.telegram_posts (
            id String,
            channel_id String,
            channel_username String,
            channel_title String,
            message_id UInt32,
            text String,
            date DateTime,
            views UInt32,
            forwards UInt32,
            replies UInt32,
            media_type String,
            media_url String,
            has_links UInt8,
            links Array(String),
            extremism_percentage Float32,
            risk_level String,
            analysis_method String,
            keywords_matched Array(String),
            parsed_date DateTime DEFAULT now(),
            source String DEFAULT 'telegram'
        ) ENGINE = MergeTree()
        ORDER BY (date, id)
        PARTITION BY toYYYYMM(date)
        """
        
        # Общая таблица для всех социальных сетей
        all_social_posts_sql = """
        CREATE TABLE IF NOT EXISTS social_media.all_posts (
            id String,
            platform String,
            author_id String,
            author_name String,
            text String,
            created_at DateTime,
            engagement_metrics String,
            extremism_percentage Float32,
            risk_level String,
            analysis_method String,
            keywords_matched Array(String),
            parsed_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (created_at, platform, id)
        PARTITION BY (platform, toYYYYMM(created_at))
        """
        
        # Таблица для статистики парсинга
        parsing_stats_sql = """
        CREATE TABLE IF NOT EXISTS social_media.parsing_stats (
            id String,
            platform String,
            start_time DateTime,
            end_time DateTime,
            total_posts UInt32,
            extremist_posts UInt32,
            keywords Array(String),
            status String,
            error_message String,
            parsed_date DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        ORDER BY (start_time, platform)
        PARTITION BY toYYYYMM(start_time)
        """
        
        # Создаем таблицы
        tables = [
            ("twitter_posts", twitter_posts_sql),
            ("vk_posts", vk_posts_sql),
            ("ok_posts", ok_posts_sql),
            ("telegram_posts", telegram_posts_sql),
            ("all_posts", all_social_posts_sql),
            ("parsing_stats", parsing_stats_sql)
        ]
        
        for table_name, sql in tables:
            try:
                client.command(sql)
                logger.info(f"Таблица social_media.{table_name} создана")
            except Exception as e:
                logger.error(f"Ошибка создания таблицы {table_name}: {e}")
        
        logger.info("Все таблицы социальных сетей созданы успешно")
        
    except Exception as e:
        logger.error(f"Ошибка создания базы данных: {e}")
        raise
    finally:
        client.close()

if __name__ == "__main__":
    create_social_media_database()