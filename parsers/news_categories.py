"""Модуль для категоризации новостей по ключевым словам.

Этот модуль содержит:
- Словари ключевых слов для различных категорий новостей
- Функции для автоматической категоризации текстов
- Обновление категорий в базе данных ClickHouse
- Поддержка категорий: Украина, Ближний восток, Фейки, Инфовойна и др.
"""

import re
from clickhouse_driver import Client
import sys
import os

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Категория: Украина
UKRAINE_KEYWORDS = [
    'украин', 'киев', 'зеленск', 'харьков', 'одесс', 'львов', 'донбасс', 'донецк', 'луганск',
    'всу', 'афу', 'крым', 'херсон', 'николаев', 'запорожье', 'мариуполь',
    'укр', 'незалежн', 'хохл', 'бандер', 'азов', 'айдар', 'нацбат',
    'порошенко', 'тимошенко', 'яценюк', 'турчинов', 'аваков', 'кличко',
    'майдан', 'евромайдан', 'оун', 'упа', 'схрон', 'схід', 'захід',
    'укрзализныця', 'укрэнерго', 'нафтогаз', 'укроборонпром'
]

# Категория: Ближний восток
MIDDLE_EAST_KEYWORDS = [
    'израил', 'палестин', 'газ', 'хамас', 'сектор газа', 'тель-авив', 'иерусалим', 'нетаньяху',
    'хезболла', 'ливан', 'бейрут', 'сири', 'дамаск', 'асад', 'идлиб', 'алеппо',
    'иран', 'тегеран', 'хаменеи', 'ирак', 'багдад', 'курд', 'пешмерга',
    'саудовск', 'эр-рияд', 'йемен', 'хути', 'сана', 'аден', 'оаэ', 'катар', 'доха',
    'турц', 'анкар', 'эрдоган', 'стамбул', 'иордан', 'амман', 'египет', 'каир',
    'синай', 'игил', 'исламск', 'джихад', 'талибан', 'моссад', 'цахал'
]

# Категория: Фейки
FAKE_NEWS_KEYWORDS = [
    'фейк', 'опроверг', 'ложн', 'недостоверн', 'манипуляц', 'дезинформац',
    'слух', 'вброс', 'постанов', 'инсценир', 'монтаж', 'фотошоп', 'фальсификац',
    'мистификац', 'обман', 'неправд', 'искажен', 'подделк', 'фальшив',
    'фактчек', 'проверк', 'разоблач', 'опроверж', 'фактоид', 'мистификац',
    'фальсификат', 'фальсифицир', 'фальшивк', 'подлог', 'фальшивомонетчик'
]

# Категория: Инфовойна
INFO_WAR_KEYWORDS = [
    'пропаганд', 'информационн', 'кибер', 'хакер', 'взлом', 'утечк', 'слив',
    'разведк', 'шпион', 'агент', 'спецслужб', 'фсб', 'цру', 'ми-6', 'моссад',
    'дезинформ', 'манипул', 'психологическ', 'операц', 'влияни', 'вмешательств',
    'троллинг', 'бот', 'ферм', 'фабрик', 'кремлебот', 'либераст', 'методичк',
    'нарратив', 'дискурс', 'риторик', 'информационн', 'атак', 'гибридн',
    'мягк', 'сил', 'когнитивн', 'искажени', 'восприяти', 'сознани',
    'общественн', 'мнени', 'массов', 'сознани', 'промывк', 'мозг'
]

# Категория: Европа
EUROPE_KEYWORDS = [
    'европ', 'ес', 'евросоюз', 'еврокомисс', 'брюссель', 'страсбург',
    'герман', 'берлин', 'франц', 'париж', 'великобритан', 'лондон',
    'итал', 'рим', 'испан', 'мадрид', 'польш', 'варшав', 'чех', 'прага',
    'венгр', 'будапешт', 'австр', 'вена', 'швец', 'стокгольм', 'норвег', 'осло',
    'финлянд', 'хельсинк', 'дан', 'копенгаген', 'нидерланд', 'голланд', 'амстердам',
    'бельг', 'брюссель', 'швейцар', 'берн', 'балкан', 'балти',
    'шольц', 'макрон', 'сунак', 'меланони', 'санчес', 'орбан',
    'нато', 'альянс', 'евро', 'шенген', 'брексит', 'мигрант', 'беженц'
]

# Категория: США
USA_KEYWORDS = [
    'сша', 'америк', 'штат', 'вашингтон', 'нью-йорк', 'белый дом', 'пентагон',
    'госдеп', 'госдепартамент', 'цру', 'фбр', 'нса', 'байден', 'трамп', 'обама',
    'клинтон', 'буш', 'рейган', 'конгресс', 'сенат', 'палата представител',
    'республиканц', 'демократ', 'либертарианц', 'импичмент', 'выбор',
    'доллар', 'уолл-стрит', 'фрс', 'федрезерв', 'калифорн', 'техас', 'флорид',
    'аляск', 'гавай', 'невад', 'аризон', 'нью-джерси', 'массачусетс',
    'пенсильван', 'огайо', 'мичиган', 'иллинойс', 'чикаго', 'лос-анджелес',
    'сан-франциско', 'бостон', 'филадельфи', 'детройт', 'сиэтл', 'майами'
]


def classify_news(title, content):
    """Классифицирует новость по категориям на основе ключевых слов
    
    Args:
        title (str): Заголовок новости
        content (str): Содержание новости
        
    Returns:
        str: Категория новости (ukraine, middle_east, fake_news, info_war, europe, usa)
              или 'other' если не удалось классифицировать
    """
    # Объединяем заголовок и содержание для поиска ключевых слов
    text = (title + " " + content).lower()
    
    # Словарь для подсчета совпадений по каждой категории
    category_matches = {
        'ukraine': 0,
        'middle_east': 0,
        'fake_news': 0,
        'info_war': 0,
        'europe': 0,
        'usa': 0
    }
    
    # Проверяем совпадения для каждой категории
    for keyword in UKRAINE_KEYWORDS:
        if keyword.lower() in text:
            category_matches['ukraine'] += 1
    
    for keyword in MIDDLE_EAST_KEYWORDS:
        if keyword.lower() in text:
            category_matches['middle_east'] += 1
    
    for keyword in FAKE_NEWS_KEYWORDS:
        if keyword.lower() in text:
            category_matches['fake_news'] += 1
    
    for keyword in INFO_WAR_KEYWORDS:
        if keyword.lower() in text:
            category_matches['info_war'] += 1
    
    for keyword in EUROPE_KEYWORDS:
        if keyword.lower() in text:
            category_matches['europe'] += 1
    
    for keyword in USA_KEYWORDS:
        if keyword.lower() in text:
            category_matches['usa'] += 1
    
    # Находим категорию с наибольшим количеством совпадений
    max_category = max(category_matches.items(), key=lambda x: x[1])
    
    # Если нет совпадений, возвращаем 'other'
    if max_category[1] == 0:
        return 'other'
    
    return max_category[0]


# Функция для создания таблиц для каждой категории
def create_category_tables(client):
    """Создает таблицы для каждой категории новостей"""
    # Список категорий
    categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
    
    # Список всех источников новостей
    sources = {
        'ria': {'table_suffix': 'ria', 'default_source': 'ria.ru', 'extra_fields': ''},
        'israil': {'table_suffix': 'israil', 'default_source': '7kanal.co.il', 'extra_fields': 'source_links String,'},
        'telegram': {'table_suffix': 'telegram', 'default_source': 'telegram', 'extra_fields': 'channel String, message_id Int64, message_link String,'},
        'lenta': {'table_suffix': 'lenta', 'default_source': 'lenta.ru', 'extra_fields': ''},
        'rbc': {'table_suffix': 'rbc', 'default_source': 'rbc.ru', 'extra_fields': ''},
        'cnn': {'table_suffix': 'cnn', 'default_source': 'cnn.com', 'extra_fields': ''},
        'aljazeera': {'table_suffix': 'aljazeera', 'default_source': 'aljazeera.com', 'extra_fields': ''},
        'tsn': {'table_suffix': 'tsn', 'default_source': 'tsn.ua', 'extra_fields': ''},
        'unian': {'table_suffix': 'unian', 'default_source': 'unian.net', 'extra_fields': ''},
        'rt': {'table_suffix': 'rt', 'default_source': 'rt.com', 'extra_fields': ''},
        'euronews': {'table_suffix': 'euronews', 'default_source': 'euronews.com', 'extra_fields': ''},
        'reuters': {'table_suffix': 'reuters', 'default_source': 'reuters.com', 'extra_fields': ''},
        'france24': {'table_suffix': 'france24', 'default_source': 'france24.com', 'extra_fields': ''},
        'dw': {'table_suffix': 'dw', 'default_source': 'dw.com', 'extra_fields': ''},
        'bbc': {'table_suffix': 'bbc', 'default_source': 'bbc.com', 'extra_fields': ''},
        'gazeta': {'table_suffix': 'gazeta', 'default_source': 'gazeta.ru', 'extra_fields': ''},
        'kommersant': {'table_suffix': 'kommersant', 'default_source': 'kommersant.ru', 'extra_fields': ''}
    }
    
    # Создаем таблицы для каждого источника и каждой категории
    for source_key, source_info in sources.items():
        for category in categories:
            # Специальная обработка для telegram
            if source_key == 'telegram':
                client.execute(f'''
                    CREATE TABLE IF NOT EXISTS news.telegram_{category} (
                        id UUID DEFAULT generateUUIDv4(),
                        title String,
                        content String,
                        channel String,
                        message_id Int64,
                        message_link String,
                        source String DEFAULT 'telegram',
                        category String DEFAULT '{category}',
                        parsed_date DateTime DEFAULT now()
                    ) ENGINE = MergeTree()
                    ORDER BY (parsed_date, id)
                ''')
            # Специальная обработка для israil
            elif source_key == 'israil':
                client.execute(f'''
                    CREATE TABLE IF NOT EXISTS news.israil_{category} (
                        id UUID DEFAULT generateUUIDv4(),
                        title String,
                        link String,
                        content String,
                        source_links String,
                        source String DEFAULT '7kanal.co.il',
                        category String DEFAULT '{category}',
                        parsed_date DateTime DEFAULT now()
                    ) ENGINE = MergeTree()
                    ORDER BY (parsed_date, id)
                ''')
            # Стандартная структура для остальных источников
            else:
                client.execute(f'''
                    CREATE TABLE IF NOT EXISTS news.{source_info["table_suffix"]}_{category} (
                        id UUID DEFAULT generateUUIDv4(),
                        title String,
                        link String,
                        content String,
                        source String DEFAULT '{source_info["default_source"]}',
                        category String DEFAULT '{category}',
                        parsed_date DateTime DEFAULT now()
                    ) ENGINE = MergeTree()
                    ORDER BY (parsed_date, id)
                ''')


# Функция для перемещения существующих данных в категоризированные таблицы
def migrate_existing_data():
    """Перемещает существующие данные в таблицы по категориям"""
    client = Client(
        host=Config.CLICKHOUSE_HOST,
        port=Config.CLICKHOUSE_NATIVE_PORT,
        user=Config.CLICKHOUSE_USER,
        password=Config.CLICKHOUSE_PASSWORD
    )
    
    # Создаем таблицы для категорий, если они не существуют
    create_category_tables(client)
    
    # Получаем все записи из таблицы RIA
    ria_data = client.execute('''
        SELECT id, title, link, content, source, category, parsed_date
        FROM news.ria_headlines
    ''')
    
    # Получаем все записи из таблицы Telegram
    telegram_data = client.execute('''
        SELECT id, title, content, channel, message_id, message_link, parsed_date
        FROM news.telegram_headlines
    ''')
    
    # Словари для хранения данных по категориям
    ria_categorized_data = {
        'ukraine': [],
        'middle_east': [],
        'fake_news': [],
        'info_war': [],
        'europe': [],
        'usa': [],
        'other': []
    }
    
    telegram_categorized_data = {
        'ukraine': [],
        'middle_east': [],
        'fake_news': [],
        'info_war': [],
        'europe': [],
        'usa': [],
        'other': []
    }
    
    # Классифицируем каждую запись RIA
    for row in ria_data:
        id_val, title, link, content, source, old_category, parsed_date = row
        new_category = classify_news(title, content)
        
        # Добавляем запись в соответствующую категорию
        ria_categorized_data[new_category].append({
            'id': id_val,
            'title': title,
            'link': link,
            'content': content,
            'source': source,
            'category': new_category,
            'parsed_date': parsed_date
        })
    
    # Вставляем данные в соответствующие таблицы
    for category, data in ria_categorized_data.items():
        if data:  # Если есть данные для этой категории
            client.execute(
                f'INSERT INTO news.ria_{category} (id, title, link, content, source, category, parsed_date) VALUES',
                data
            )
    
    # Получаем все записи из таблицы Israil
    israil_data = client.execute('''
        SELECT id, title, link, content, source_links, source, category, parsed_date
        FROM news.israil_headlines
    ''')
    
    # Словари для хранения данных по категориям
    israil_categorized_data = {
        'ukraine': [],
        'middle_east': [],
        'fake_news': [],
        'info_war': [],
        'europe': [],
        'usa': [],
        'other': []
    }
    
    # Классифицируем каждую запись Israil
    for row in israil_data:
        id_val, title, link, content, source_links, source, old_category, parsed_date = row
        new_category = classify_news(title, content)
        
        # Добавляем запись в соответствующую категорию
        israil_categorized_data[new_category].append({
            'id': id_val,
            'title': title,
            'link': link,
            'content': content,
            'source_links': source_links,
            'source': source,
            'category': new_category,
            'parsed_date': parsed_date
        })
    
    # Вставляем данные в соответствующие таблицы
    for category, data in israil_categorized_data.items():
        if data:  # Если есть данные для этой категории
            client.execute(
                f'INSERT INTO news.israil_{category} (id, title, link, content, source_links, source, category, parsed_date) VALUES',
                data
            )
    
    # Классифицируем каждую запись Telegram
    for row in telegram_data:
        id_val, title, content, channel, message_id, message_link, parsed_date = row
        new_category = classify_news(title, content)
        
        # Добавляем запись в соответствующую категорию
        telegram_categorized_data[new_category].append({
            'id': id_val,
            'title': title,
            'content': content,
            'channel': channel,
            'message_id': message_id,
            'message_link': message_link,
            'source': 'telegram',
            'category': new_category,
            'parsed_date': parsed_date
        })
    
    # Вставляем данные Telegram в соответствующие таблицы
    for category, data in telegram_categorized_data.items():
        if data:  # Если есть данные для этой категории
            client.execute(
                f'INSERT INTO news.telegram_{category} (id, title, content, channel, message_id, message_link, source, category, parsed_date) VALUES',
                data
            )
    
    print("Миграция данных завершена.")
    
    # Статистика по категориям
    for category in ria_categorized_data.keys():
        ria_count = len(ria_categorized_data[category])
        israil_count = len(israil_categorized_data[category])
        print(f"Категория {category}: RIA - {ria_count}, Israil - {israil_count}")


if __name__ == "__main__":
    migrate_existing_data()