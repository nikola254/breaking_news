"""Модуль для категоризации новостей по украинскому конфликту.

Этот модуль содержит:
- Словари ключевых слов для 5 категорий украинского конфликта
- Функции для автоматической категоризации текстов
- AI-фильтр для определения релевантности к теме Украины и СВО
- Обновление категорий в базе данных ClickHouse

Категории:
1. Военные операции - боевые действия, тактические манёвры, потери военных, захват территорий
2. Гуманитарный кризис - разрушение инфраструктуры, доступ к воде/электричеству, перемещение населения
3. Экономические последствия - санкции, инфляция, цены на товары, влияние на рынок труда и энергетику
4. Политические решения - внутренние законы, международные соглашения, мобилизация, дипломатические шаги
5. Информационно-социальные аспекты - дезинформация, пропаганда, общественные протесты, настроения населения
"""

import re
import logging
from clickhouse_driver import Client
import sys
import os
import requests
import json
from flask import current_app

# Настройка логирования
logger = logging.getLogger(__name__)

# Добавляем корневую директорию проекта в sys.path для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import Config

# Базовые ключевые слова для определения релевантности к украинскому конфликту
UKRAINE_CONFLICT_KEYWORDS = [
    # Основные термины конфликта
    'украин', 'россия', 'сво', 'спецоперац', 'военн', 'конфликт', 'война',
    'ukraine', 'russia', 'war', 'conflict', 'military', 'operation',
    
    # Географические названия
    'киев', 'харьков', 'одесс', 'львов', 'донбасс', 'донецк', 'луганск',
    'крым', 'херсон', 'николаев', 'запорожье', 'мариуполь', 'бахмут', 'авдеевк',
    'kyiv', 'kharkiv', 'odesa', 'lviv', 'donbas', 'donetsk', 'luhansk',
    'crimea', 'kherson', 'mykolaiv', 'zaporizhzhia', 'mariupol', 'bakhmut', 'avdiivka',
    
    # Военные формирования и лидеры
    'всу', 'афу', 'вс рф', 'росгвард', 'чвк', 'вагнер', 'азов',
    'зеленск', 'путин', 'шойгу', 'герасимов', 'пригожин',
    'zelensky', 'putin', 'shoigu', 'gerasimov', 'prigozhin',
    
    # Военная техника и оружие
    'химарс', 'джавелин', 'байрактар', 'искандер', 'калибр', 'кинжал',
    'himars', 'javelin', 'bayraktar', 'iskander', 'caliber', 'kinzhal',
    'танк', 'бтр', 'бмп', 'рсзо', 'пво', 'беспилотник', 'дрон',
    'tank', 'apc', 'ifv', 'mlrs', 'air defense', 'drone', 'uav'
]

# Категория 1: Военные операции
MILITARY_OPERATIONS_KEYWORDS = [
    # Боевые действия
    'атак', 'наступлен', 'оборон', 'штурм', 'бомбардировк', 'обстрел', 'удар',
    'attack', 'offensive', 'defense', 'assault', 'bombardment', 'shelling', 'strike',
    
    # Тактические манёвры
    'операц', 'манёвр', 'прорыв', 'окружен', 'отступлен', 'контратак', 'рейд',
    'operation', 'maneuver', 'breakthrough', 'encirclement', 'retreat', 'counterattack', 'raid',
    
    # Потери военных
    'потер', 'убит', 'ранен', 'пропал без вести', 'пленн', 'жертв', 'погиб',
    'casualties', 'killed', 'wounded', 'missing', 'captured', 'victims', 'died',
    
    # Захват территорий
    'захват', 'освобожден', 'занят', 'контрол', 'территор', 'позиц', 'рубеж',
    'capture', 'liberated', 'occupied', 'control', 'territory', 'position', 'line',
    
    # Военные подразделения
    'батальон', 'полк', 'бригад', 'дивизи', 'корпус', 'армия', 'фронт',
    'battalion', 'regiment', 'brigade', 'division', 'corps', 'army', 'front'
]

# Категория 2: Гуманитарный кризис
HUMANITARIAN_CRISIS_KEYWORDS = [
    # Разрушение инфраструктуры
    'разруш', 'повреж', 'уничтож', 'взрыв', 'снос', 'демонтаж',
    'destroyed', 'damaged', 'demolished', 'explosion', 'demolition',
    
    # Инфраструктурные объекты
    'больниц', 'школ', 'детсад', 'мост', 'дорог', 'аэропорт', 'вокзал',
    'hospital', 'school', 'kindergarten', 'bridge', 'road', 'airport', 'station',
    
    # Доступ к воде/электричеству
    'электричеств', 'вод', 'газ', 'отоплен', 'канализац', 'водопровод',
    'electricity', 'water', 'gas', 'heating', 'sewage', 'plumbing',
    'отключен', 'авари', 'энергосистем', 'энергетик', 'электростанц',
    'blackout', 'outage', 'power grid', 'energy', 'power plant',
    
    # Перемещение населения
    'беженц', 'эвакуац', 'переселен', 'мигрант', 'перемещен', 'покинул',
    'refugee', 'evacuation', 'relocation', 'migrant', 'displaced', 'fled',
    
    # Помощь беженцам
    'гуманитарн', 'помощь', 'продовольств', 'медикамент', 'одежд', 'приют',
    'humanitarian', 'aid', 'food', 'medicine', 'clothing', 'shelter',
    'красный крест', 'оон', 'увкб', 'unicef',
    'red cross', 'un', 'unhcr', 'unicef'
]

# Категория 3: Экономические последствия
ECONOMIC_CONSEQUENCES_KEYWORDS = [
    # Санкции
    'санкц', 'ограничен', 'запрет', 'эмбарго', 'блокад', 'заморозк',
    'sanctions', 'restrictions', 'ban', 'embargo', 'blockade', 'freeze',
    
    # Инфляция и цены
    'инфляц', 'цен', 'подорожан', 'рост цен', 'стоимость', 'тариф',
    'inflation', 'prices', 'price increase', 'cost', 'tariff',
    
    # Товары и услуги
    'продовольств', 'топлив', 'энерг', 'нефт', 'газ', 'уголь',
    'food', 'fuel', 'energy', 'oil', 'gas', 'coal',
    'пшениц', 'зерн', 'удобрен', 'металл', 'сырь',
    'wheat', 'grain', 'fertilizer', 'metal', 'raw materials',
    
    # Рынок труда
    'безработиц', 'занятость', 'зарплат', 'доход', 'бюджет', 'налог',
    'unemployment', 'employment', 'salary', 'income', 'budget', 'tax',
    
    # Финансовые институты
    'банк', 'swift', 'валют', 'рубль', 'доллар', 'евро', 'курс',
    'bank', 'swift', 'currency', 'ruble', 'dollar', 'euro', 'exchange rate',
    'центробанк', 'цб', 'фрс', 'ецб',
    'central bank', 'fed', 'ecb'
]

# Категория 4: Политические решения
POLITICAL_DECISIONS_KEYWORDS = [
    # Внутренние законы
    'закон', 'законопроект', 'указ', 'постановлен', 'решен', 'принят',
    'law', 'bill', 'decree', 'resolution', 'decision', 'adopted',
    
    # Мобилизация
    'мобилизац', 'призыв', 'военкомат', 'повестк', 'служб', 'армия',
    'mobilization', 'conscription', 'draft', 'military service', 'army',
    
    # Международные соглашения
    'договор', 'соглашен', 'пакт', 'альянс', 'союз', 'партнерств',
    'treaty', 'agreement', 'pact', 'alliance', 'union', 'partnership',
    
    # Дипломатические шаги
    'дипломат', 'переговор', 'встреч', 'саммит', 'консультац', 'диалог',
    'diplomatic', 'negotiations', 'meeting', 'summit', 'consultation', 'dialogue',
    
    # Политические лидеры и институты
    'президент', 'премьер', 'министр', 'парламент', 'дума', 'сенат',
    'president', 'prime minister', 'minister', 'parliament', 'senate',
    'нато', 'ес', 'оон', 'обсе', 'g7', 'g20',
    'nato', 'eu', 'un', 'osce', 'g7', 'g20'
]

# Категория 5: Информационно-социальные аспекты
INFO_SOCIAL_KEYWORDS = [
    # Дезинформация
    'дезинформац', 'фейк', 'ложн', 'недостоверн', 'манипуляц', 'вброс',
    'disinformation', 'fake', 'false', 'unreliable', 'manipulation',
    
    # Пропаганда
    'пропаганд', 'агитац', 'промывк', 'зомбировани', 'идеолог',
    'propaganda', 'agitation', 'brainwashing', 'ideology',
    
    # Общественные протесты
    'протест', 'митинг', 'демонстрац', 'акц', 'забастовк', 'бунт',
    'protest', 'rally', 'demonstration', 'action', 'strike', 'riot',
    
    # Настроения населения
    'настроен', 'мнени', 'опрос', 'рейтинг', 'поддержк', 'одобрен',
    'mood', 'opinion', 'poll', 'rating', 'support', 'approval',
    
    # Информационные каналы
    'сми', 'телевидени', 'радио', 'интернет', 'соцсет', 'телеграм',
    'media', 'television', 'radio', 'internet', 'social networks', 'telegram',
    
    # Цензура и контроль
    'цензур', 'блокировк', 'запрет', 'ограничен', 'контрол', 'фильтрац',
    'censorship', 'blocking', 'ban', 'restriction', 'control', 'filtering'
]


def is_ukraine_conflict_relevant(title, content):
    """Определяет, относится ли новость к украинскому конфликту
    
    Args:
        title (str): Заголовок новости
        content (str): Содержание новости
        
    Returns:
        bool: True если новость релевантна украинскому конфликту
    """
    text = (title + " " + content).lower()
    
    # Подсчитываем количество совпадений с базовыми ключевыми словами
    matches = 0
    for keyword in UKRAINE_CONFLICT_KEYWORDS:
        if keyword.lower() in text:
            matches += 1
    
    # Считаем релевантным, если найдено хотя бы 2 совпадения
    return matches >= 2


def classify_ukraine_news(title, content):
    """Классифицирует новость по 5 категориям украинского конфликта
    
    Args:
        title (str): Заголовок новости
        content (str): Содержание новости
        
    Returns:
        str: Категория новости или None если не релевантна украинскому конфликту
    """
    # Сначала проверяем релевантность
    if not is_ukraine_conflict_relevant(title, content):
        return None
    
    text = (title + " " + content).lower()
    
    # Словарь для подсчета совпадений по каждой категории
    category_matches = {
        'military_operations': 0,
        'humanitarian_crisis': 0,
        'economic_consequences': 0,
        'political_decisions': 0,
        'information_social': 0
    }
    
    # Проверяем совпадения для каждой категории
    for keyword in MILITARY_OPERATIONS_KEYWORDS:
        if keyword.lower() in text:
            category_matches['military_operations'] += 1
    
    for keyword in HUMANITARIAN_CRISIS_KEYWORDS:
        if keyword.lower() in text:
            category_matches['humanitarian_crisis'] += 1
    
    for keyword in ECONOMIC_CONSEQUENCES_KEYWORDS:
        if keyword.lower() in text:
            category_matches['economic_consequences'] += 1
    
    for keyword in POLITICAL_DECISIONS_KEYWORDS:
        if keyword.lower() in text:
            category_matches['political_decisions'] += 1
    
    for keyword in INFO_SOCIAL_KEYWORDS:
        if keyword.lower() in text:
            category_matches['information_social'] += 1
    
    # Находим категорию с наибольшим количеством совпадений
    max_category = max(category_matches.items(), key=lambda x: x[1])
    
    # Если нет совпадений, возвращаем None
    if max_category[1] == 0:
        return None
    
    return max_category[0]


def classify_news(title, content):
    """Функция для обратной совместимости с парсерами
    
    Args:
        title (str): Заголовок новости
        content (str): Содержание новости
        
    Returns:
        str: Категория новости в старом формате
    """
    # Используем новую функцию классификации
    category = classify_ukraine_news(title, content)
    
    if category is None:
        return 'other'
    
    # Маппинг новых категорий к старым названиям для совместимости
    category_mapping = {
        'military_operations': 'ukraine_conflict_military',
        'humanitarian_crisis': 'ukraine_conflict_humanitarian', 
        'economic_consequences': 'ukraine_conflict_economic',
        'political_decisions': 'ukraine_conflict_political',
        'information_social': 'ukraine_conflict_information_social'
    }
    
    return category_mapping.get(category, 'other')


def ai_classify_ukraine_news(title, content):
    """Использует AI для более точной классификации новостей
    
    Args:
        title (str): Заголовок новости
        content (str): Содержание новости
        
    Returns:
        dict: {'category': str, 'confidence': float, 'is_relevant': bool}
    """
    try:
        # Получаем API ключ из конфигурации
        api_key = current_app.config.get('API_KEY') if current_app else os.getenv('API_KEY')
        
        if not api_key:
            logger.warning("API_KEY не найден, используем базовую классификацию")
            category = classify_ukraine_news(title, content)
            return {
                'category': category,
                'confidence': 0.7 if category else 0.0,
                'is_relevant': category is not None
            }
        
        # Формируем промпт для AI
        prompt = f"""Проанализируй следующую новость и определи:
1. Относится ли она к украинскому конфликту/СВО (да/нет)
2. Если да, к какой из 5 категорий она относится:
   - military_operations (военные операции)
   - humanitarian_crisis (гуманитарный кризис)
   - economic_consequences (экономические последствия)
   - political_decisions (политические решения)
   - information_social (информационно-социальные аспекты)

Заголовок: {title}
Текст: {content[:1000]}...

Ответь в формате JSON: {{"is_relevant": true/false, "category": "название_категории", "confidence": 0.0-1.0}}"""
        
        # Отправляем запрос к Cloud.ru API
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [
                {'role': 'system', 'content': 'Ты эксперт по анализу новостей о украинском конфликте. Отвечай только в формате JSON.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 200,
            'temperature': 0.1
        }
        
        response = requests.post(
            'https://api.cloudru.ai/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            try:
                # Парсим JSON ответ от AI
                ai_result = json.loads(ai_response)
                return {
                    'category': ai_result.get('category') if ai_result.get('is_relevant') else None,
                    'confidence': ai_result.get('confidence', 0.8),
                    'is_relevant': ai_result.get('is_relevant', False)
                }
            except json.JSONDecodeError:
                logger.error(f"Ошибка парсинга JSON ответа от AI: {ai_response}")
        else:
            logger.error(f"Ошибка API запроса: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Ошибка AI классификации: {e}")
    
    # Fallback на базовую классификацию
    category = classify_ukraine_news(title, content)
    return {
        'category': category,
        'confidence': 0.7 if category else 0.0,
        'is_relevant': category is not None
    }


def create_ukraine_conflict_tables(client):
    """Создает таблицы для украинского конфликта"""
    categories = ['ukraine_conflict_military', 'ukraine_conflict_humanitarian', 'ukraine_conflict_diplomatic', 
                 'ukraine_conflict_economic', 'ukraine_conflict_international']
    
    # Список всех источников новостей
    sources = {
        'ria': {'table_suffix': 'ria', 'default_source': 'ria.ru'},
        'lenta': {'table_suffix': 'lenta', 'default_source': 'lenta.ru'},
        'rbc': {'table_suffix': 'rbc', 'default_source': 'rbc.ru'},
        'cnn': {'table_suffix': 'cnn', 'default_source': 'cnn.com'},
        'bbc': {'table_suffix': 'bbc', 'default_source': 'bbc.com'},
        'reuters': {'table_suffix': 'reuters', 'default_source': 'reuters.com'},
        'aljazeera': {'table_suffix': 'aljazeera', 'default_source': 'aljazeera.com'},
        'rt': {'table_suffix': 'rt', 'default_source': 'rt.com'},
        'euronews': {'table_suffix': 'euronews', 'default_source': 'euronews.com'},
        'dw': {'table_suffix': 'dw', 'default_source': 'dw.com'},
        'france24': {'table_suffix': 'france24', 'default_source': 'france24.com'},
        'tsn': {'table_suffix': 'tsn', 'default_source': 'tsn.ua'},
        'unian': {'table_suffix': 'unian', 'default_source': 'unian.net'},
        'kommersant': {'table_suffix': 'kommersant', 'default_source': 'kommersant.ru'},
        'gazeta': {'table_suffix': 'gazeta', 'default_source': 'gazeta.ru'},
        'telegram': {'table_suffix': 'telegram', 'default_source': 'telegram'}
    }
    
    try:
        # Создаем основную таблицу для всех украинских новостей
        client.execute('''
            CREATE TABLE IF NOT EXISTS news.ukraine_conflict_all (
                id UUID DEFAULT generateUUIDv4(),
                title String,
                link String,
                content String,
                source String,
                category String,
                confidence Float32 DEFAULT 0.0,
                sentiment Float32 DEFAULT 0.0,
                published_date DateTime DEFAULT now(),
                language String DEFAULT 'unknown',
                metadata String DEFAULT '{}'
            ) ENGINE = MergeTree()
            ORDER BY (published_date, category, id)
        ''')
        
        # Создаем таблицы для каждой категории
        for category in categories:
            for source_key, source_info in sources.items():
                table_name = f"{source_info['table_suffix']}_{category}"
                
                # Дополнительные поля для Telegram
                extra_fields = ''
                if source_key == 'telegram':
                    extra_fields = '''
                        channel String DEFAULT '',
                        message_id Int64 DEFAULT 0,
                        message_link String DEFAULT '','''
                
                client.execute(f'''
                    CREATE TABLE IF NOT EXISTS news.{table_name} (
                        id UUID DEFAULT generateUUIDv4(),
                        title String,
                        link String,
                        content String,
                        source String DEFAULT '{source_info["default_source"]}',
                        category String DEFAULT '{category}',
                        confidence Float32 DEFAULT 0.0,
                        sentiment Float32 DEFAULT 0.0,
                        {extra_fields}
                        published_date DateTime DEFAULT now(),
                        language String DEFAULT 'unknown',
                        metadata String DEFAULT '{{}}'
                    ) ENGINE = MergeTree()
                    ORDER BY (published_date, id)
                ''')
        
        logger.info("Созданы таблицы для украинского конфликта")
        
    except Exception as e:
        logger.error(f"Ошибка создания таблиц: {e}")


def create_category_tables(client):
    """Создает таблицы для каждой категории новостей"""
    
    # Список категорий
    categories = ['ukraine', 'middle_east', 'fake_news', 'info_war', 'europe', 'usa', 'other']
    
    # Список всех источников новостей
    sources = {
        'ria': {'table_suffix': 'ria', 'default_source': 'ria.ru'},
        'israil': {'table_suffix': 'israil', 'default_source': '7kanal.co.il'},
        'telegram': {'table_suffix': 'telegram', 'default_source': 'telegram'},
        'lenta': {'table_suffix': 'lenta', 'default_source': 'lenta.ru'},
        'rbc': {'table_suffix': 'rbc', 'default_source': 'rbc.ru'},
        'cnn': {'table_suffix': 'cnn', 'default_source': 'cnn.com'},
        'aljazeera': {'table_suffix': 'aljazeera', 'default_source': 'aljazeera.com'},
        'tsn': {'table_suffix': 'tsn', 'default_source': 'tsn.ua'},
        'unian': {'table_suffix': 'unian', 'default_source': 'unian.net'},
        'rt': {'table_suffix': 'rt', 'default_source': 'rt.com'},
        'euronews': {'table_suffix': 'euronews', 'default_source': 'euronews.com'},
        'reuters': {'table_suffix': 'reuters', 'default_source': 'reuters.com'},
        'france24': {'table_suffix': 'france24', 'default_source': 'france24.com'},
        'dw': {'table_suffix': 'dw', 'default_source': 'dw.com'},
        'bbc': {'table_suffix': 'bbc', 'default_source': 'bbc.com'},
        'gazeta': {'table_suffix': 'gazeta', 'default_source': 'gazeta.ru'},
        'kommersant': {'table_suffix': 'kommersant', 'default_source': 'kommersant.ru'}
    }
    
    print("\nСоздание таблиц категорий:")
    
    # Создаем таблицы для каждого источника и каждой категории
    for source_key, source_info in sources.items():
        for category in categories:
            try:
                # Специальная обработка для telegram
                if source_key == 'telegram':
                    query = f'''
                        CREATE TABLE IF NOT EXISTS news.telegram_{category} (
                            id UUID DEFAULT generateUUIDv4(),
                            title String,
                            content String,
                            channel String,
                            message_id Int64,
                            message_link String,
                            source String DEFAULT 'telegram',
                            category String DEFAULT '{category}',
                            published_date DateTime DEFAULT now()
                        ) ENGINE = MergeTree()
                        ORDER BY (published_date, id)
                    '''
                # Специальная обработка для israil
                elif source_key == 'israil':
                    query = f'''
                        CREATE TABLE IF NOT EXISTS news.israil_{category} (
                            id UUID DEFAULT generateUUIDv4(),
                            title String,
                            link String,
                            content String,
                            source_links String,
                            source String DEFAULT '7kanal.co.il',
                            category String DEFAULT '{category}',
                            published_date DateTime DEFAULT now()
                        ) ENGINE = MergeTree()
                        ORDER BY (published_date, id)
                    '''
                # Стандартная структура для остальных источников
                else:
                    query = f'''
                        CREATE TABLE IF NOT EXISTS news.{source_info["table_suffix"]}_{category} (
                            id UUID DEFAULT generateUUIDv4(),
                            title String,
                            link String,
                            content String,
                            source String DEFAULT '{source_info["default_source"]}',
                            category String DEFAULT '{category}',
                            published_date DateTime DEFAULT now()
                        ) ENGINE = MergeTree()
                        ORDER BY (published_date, id)
                    '''
                
                client.execute(query)
                print(f"✓ Таблица {source_info['table_suffix']}_{category} создана")
                
            except Exception as e:
                print(f"✗ Ошибка при создании таблицы {source_info['table_suffix']}_{category}: {e}")


def get_category_display_name(category):
    """Возвращает человекочитаемое название категории"""
    category_names = {
        'ukraine_conflict_military': 'Военные операции',
        'ukraine_conflict_humanitarian': 'Гуманитарный кризис',
        'ukraine_conflict_diplomatic': 'Дипломатия и переговоры',
        'ukraine_conflict_economic': 'Экономические последствия',
        'ukraine_conflict_international': 'Международная реакция'
    }
    return category_names.get(category, category)


if __name__ == "__main__":
    # Создаем подключение к ClickHouse
    try:
        client = Client(
            host=Config.CLICKHOUSE_HOST,
            port=Config.CLICKHOUSE_NATIVE_PORT,
            user=Config.CLICKHOUSE_USER,
            password=Config.CLICKHOUSE_PASSWORD,
            database=Config.CLICKHOUSE_DATABASE
        )
        
        # Создаем таблицы
        create_ukraine_conflict_tables(client)
        print("Таблицы для украинского конфликта созданы успешно")
        
    except Exception as e:
        print(f"Ошибка: {e}")
