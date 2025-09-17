import os
import logging
import requests
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UkraineRelevanceFilter:
    """Фильтр для определения релевантности новостей к украинскому конфликту и СВО"""
    
    def __init__(self):
        """Инициализация фильтра"""
        self.api_key = os.environ.get("API_KEY")
        self.base_url = "https://foundation-models.api.cloud.ru/v1"
        
        if not self.api_key:
            raise ValueError("API_KEY не найден в переменных окружения")
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.api_url = f"{self.base_url}/chat/completions"
        
        # Ключевые слова для 5 категорий украинского конфликта
        self.ukraine_keywords = {
            'military_operations': [
                # Военные операции - боевые действия, тактические манёвры, потери военных, захват территорий
                'атак', 'attack', 'наступление', 'offensive', 'контрнаступление', 'counteroffensive',
                'операция', 'operation', 'бой', 'battle', 'сражение', 'combat', 'штурм', 'assault',
                'обстрел', 'shelling', 'бомбардировк', 'bombing', 'авиаудар', 'airstrike',
                'артобстрел', 'artillery fire', 'ракетный удар', 'missile strike', 'дрон-атак', 'drone attack',
                'потери', 'casualties', 'убит', 'killed', 'ранен', 'wounded', 'погиб', 'died',
                'захват', 'capture', 'освобожден', 'liberated', 'занят', 'occupied', 'взят', 'taken',
                'фронт', 'front', 'линия фронта', 'frontline', 'позиции', 'positions',
                'всу', 'afu', 'вс рф', 'russian forces', 'чвк', 'pmc', 'вагнер', 'wagner',
                'мобилизация', 'mobilization', 'призыв', 'conscription'
            ],
            'humanitarian_crisis': [
                # Гуманитарный кризис - разрушение инфраструктуры, доступ к воде/электричеству, перемещение населения
                'разрушен', 'destroyed', 'разбомблен', 'bombed', 'повреждена инфраструктура', 'damaged infrastructure',
                'электричество', 'electricity', 'электроэнергия', 'power', 'отключение света', 'blackout',
                'водоснабжение', 'water supply', 'отопление', 'heating', 'газоснабжение', 'gas supply',
                'больниц', 'hospital', 'школ', 'school', 'детский сад', 'kindergarten',
                'жилые дома', 'residential buildings', 'многоэтажк', 'apartment building',
                'беженц', 'refugee', 'эвакуация', 'evacuation', 'переселенц', 'displaced',
                'гуманитарная помощь', 'humanitarian aid', 'красный крест', 'red cross',
                'оон', 'un', 'юнисеф', 'unicef', 'гуманитарный коридор', 'humanitarian corridor',
                'мирные жители', 'civilians', 'гражданские', 'civilian population'
            ],
            'economic_consequences': [
                # Экономические последствия - санкции, инфляция, цены на товары, влияние на рынок труда и энергетику
                'санкции', 'sanctions', 'эмбарго', 'embargo', 'ограничения', 'restrictions',
                'заморозка активов', 'asset freeze', 'блокировка счетов', 'account blocking',
                'инфляция', 'inflation', 'рост цен', 'price increase', 'подорожание', 'price rise',
                'цены на продукты', 'food prices', 'цены на топливо', 'fuel prices',
                'энергетический кризис', 'energy crisis', 'нефт', 'oil', 'газ', 'gas',
                'рынок труда', 'labor market', 'безработица', 'unemployment', 'экономика', 'economy',
                'валют', 'currency', 'рубль', 'ruble', 'доллар', 'dollar', 'евро', 'euro',
                'банк', 'bank', 'swift', 'свифт', 'платежная система', 'payment system',
                'экспорт', 'export', 'импорт', 'import', 'торговля', 'trade'
            ],
            'political_decisions': [
                # Политические решения - внутренние законы, международные соглашения, мобилизация, дипломатические шаги
                'закон', 'law', 'законопроект', 'bill', 'указ', 'decree', 'постановление', 'resolution',
                'парламент', 'parliament', 'дума', 'duma', 'рада', 'rada', 'сенат', 'senate',
                'международные соглашения', 'international agreements', 'договор', 'treaty',
                'переговоры', 'negotiations', 'дипломатия', 'diplomacy', 'саммит', 'summit',
                'нато', 'nato', 'ес', 'eu', 'оон', 'un', 'обсе', 'osce',
                'зеленский', 'zelensky', 'путин', 'putin', 'байден', 'biden',
                'лавров', 'lavrov', 'блинкен', 'blinken', 'макрон', 'macron',
                'мобилизация', 'mobilization', 'военное положение', 'martial law',
                'референдум', 'referendum', 'выборы', 'elections'
            ],
            'information_social': [
                # Информационно-социальные аспекты - дезинформация, пропаганда, общественные протесты, настроения населения
                'дезинформация', 'disinformation', 'фейк', 'fake', 'ложная информация', 'false information',
                'пропаганда', 'propaganda', 'информационная война', 'information war',
                'соцсети', 'social media', 'телеграм', 'telegram', 'фейсбук', 'facebook',
                'твиттер', 'twitter', 'ютуб', 'youtube', 'тикток', 'tiktok',
                'митинг', 'rally', 'протест', 'protest', 'демонстрация', 'demonstration',
                'общественное мнение', 'public opinion', 'настроения', 'mood', 'опрос', 'poll',
                'цензура', 'censorship', 'блокировка', 'blocking', 'запрет', 'ban',
                'сми', 'media', 'журналист', 'journalist', 'репортер', 'reporter',
                'освещение', 'coverage', 'новости', 'news'
            ],
            'geographic': [
                # Географические названия
                'украин', 'ukraine', 'киев', 'kiev', 'kyiv', 'харьков', 'kharkiv',
                'одесс', 'odesa', 'львов', 'lviv', 'донбасс', 'donbas', 'донецк', 'donetsk',
                'луганск', 'luhansk', 'крым', 'crimea', 'херсон', 'kherson',
                'николаев', 'mykolaiv', 'запорожье', 'zaporizhzhia', 'мариуполь', 'mariupol',
                'бахмут', 'bakhmut', 'авдеевк', 'avdiivka', 'белгород', 'belgorod',
                'курск', 'kursk', 'ростов', 'rostov', 'россия', 'russia'
            ]
        }
        
        logger.info("UkraineRelevanceFilter инициализирован")
    
    def is_ukraine_relevant(self, title: str, content: str, use_ai: bool = True) -> Dict[str, Any]:
        """Определяет релевантность новости к украинскому конфликту
        
        Args:
            title (str): Заголовок новости
            content (str): Содержание новости
            use_ai (bool): Использовать ли AI для анализа (по умолчанию True)
            
        Returns:
            Dict[str, Any]: Результат анализа с полями:
                - is_relevant (bool): Релевантна ли новость
                - confidence (float): Уровень уверенности (0.0-1.0)
                - category (str): Категория новости (одна из 5 категорий)
                - reason (str): Причина решения
                - keywords_found (list): Найденные ключевые слова
        """
        try:
            # Проверяем входные данные
            if not title and not content:
                return {
                    'is_relevant': False,
                    'confidence': 1.0,
                    'reason': 'Пустой заголовок и содержание',
                    'keywords_found': []
                }
            
            title = title or ""
            content = content or ""
            
            # Быстрая предварительная фильтрация по ключевым словам
            keyword_result = self._check_keywords(title, content)
            
            # Если найдены прямые ключевые слова, считаем релевантным
            if keyword_result['confidence'] >= 0.8:
                return keyword_result
            
            # Если AI отключен, возвращаем результат по ключевым словам
            if not use_ai:
                return keyword_result
            
            # Используем AI для более точного анализа
            ai_result = self._analyze_with_ai(title, content)
            
            # Комбинируем результаты
            final_confidence = max(keyword_result['confidence'], ai_result['confidence'])
            is_relevant = final_confidence >= 0.7  # Повышаем порог для более строгой фильтрации
            
            # Определяем категорию
            category = None
            if is_relevant:
                if ai_result.get('category'):
                    category = ai_result['category']
                else:
                    category = keyword_result.get('category')
            
            return {
                'is_relevant': is_relevant,
                'confidence': final_confidence,
                'relevance_score': final_confidence,
                'category': category,
                'reason': ai_result['reason'] if ai_result['confidence'] > keyword_result['confidence'] else keyword_result['reason'],
                'keywords_found': keyword_result['keywords_found']
            }
            
        except Exception as e:
            logger.error(f"Ошибка при анализе релевантности: {e}")
            return {
                'is_relevant': False,
                'confidence': 0.0,
                'relevance_score': 0.0,
                'reason': f'Ошибка анализа: {str(e)}',
                'keywords_found': []
            }
    
    def _check_keywords(self, title: str, content: str) -> Dict[str, Any]:
        """Проверяет наличие ключевых слов в тексте
        
        Args:
            title (str): Заголовок новости
            content (str): Содержание новости
            
        Returns:
            Dict[str, Any]: Результат проверки ключевых слов
        """
        text = f"{title} {content}".lower()
        found_keywords = []
        category_scores = {}
        
        # Проверяем каждую категорию ключевых слов
        for category, keywords in self.ukraine_keywords.items():
            found_in_category = []
            for keyword in keywords:
                if keyword.lower() in text:
                    found_in_category.append(keyword)
                    found_keywords.append(keyword)
            
            if found_in_category:
                category_scores[category] = len(found_in_category) / len(keywords)
        
        # Рассчитываем общий уровень уверенности и определяем категорию
        confidence = 0.0
        reason = "Ключевые слова не найдены"
        category = None
        
        if found_keywords:
            # Географические названия обязательны для релевантности
            has_geographic = 'geographic' in category_scores
            
            # Определяем основную категорию по наибольшему количеству совпадений
            main_categories = ['military_operations', 'humanitarian_crisis', 'economic_consequences', 
                             'political_decisions', 'information_social']
            
            best_category = None
            best_score = 0
            
            for cat in main_categories:
                if cat in category_scores and category_scores[cat] > best_score:
                    best_score = category_scores[cat]
                    best_category = cat
            
            # СТРОГАЯ ПРОВЕРКА: Географические названия ОБЯЗАТЕЛЬНЫ
            if has_geographic and best_category and best_score >= 0.1:
                confidence = min(0.9, 0.6 + best_score + category_scores['geographic'] * 0.3)
                category = best_category
                reason = f"Найдены географические названия и термины категории '{best_category}'"
            elif has_geographic and category_scores['geographic'] >= 0.05:
                confidence = min(0.7, 0.4 + category_scores['geographic'] * 0.5)
                reason = "Найдены географические названия, связанные с украинским конфликтом"
            else:
                # БЕЗ географических названий - НЕ релевантно
                confidence = 0.0
                reason = "Отсутствуют географические названия, связанные с Украиной"
        
        return {
            'is_relevant': confidence >= 0.5,
            'confidence': confidence,
            'relevance_score': confidence,
            'category': category,
            'reason': reason,
            'keywords_found': found_keywords
        }
    
    def _analyze_with_ai(self, title: str, content: str) -> Dict[str, Any]:
        """Анализирует релевантность с помощью AI
        
        Args:
            title (str): Заголовок новости
            content (str): Содержание новости
            
        Returns:
            Dict[str, Any]: Результат AI-анализа
        """
        try:
            prompt = self._create_relevance_prompt(title, content)
            
            data = {
                "model": "openai/gpt-oss-120b",
                "max_tokens": 150,
                "temperature": 0.1,
                "presence_penalty": 0,
                "top_p": 0.95,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"API вернул код {response.status_code}: {response.text}")
            
            response_data = response.json()
            ai_response = response_data['choices'][0]['message']['content']
            
            # Улучшенная обработка пустых ответов
            if not ai_response or ai_response.strip() == "":
                logger.warning("AI вернул пустой ответ, используем fallback к анализу по ключевым словам")
                return self._fallback_keyword_analysis(title, content)
            
            # Парсим ответ AI
            return self._parse_ai_response(ai_response)
            
        except Exception as e:
            logger.error(f"Ошибка при AI-анализе: {e}")
            return {
                'is_relevant': False,
                'confidence': 0.0,
                'relevance_score': 0.0,
                'reason': f'Ошибка AI-анализа: {str(e)}'
            }
    
    def _create_relevance_prompt(self, title: str, content: str) -> str:
        """Создает промпт для анализа релевантности
        
        Args:
            title (str): Заголовок новости
            content (str): Содержание новости
            
        Returns:
            str: Промпт для AI
        """
        # Ограничиваем длину контента
        max_content_length = 1500
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."
        
        prompt = f"""Определи, относится ли данная новость к украинскому конфликту, СВО (специальной военной операции) или событиям в Украине.

Критерии релевантности и категории:

1. ВОЕННЫЕ ОПЕРАЦИИ - боевые действия, тактические манёвры, потери военных, захват территорий
2. ГУМАНИТАРНЫЙ КРИЗИС - разрушение инфраструктуры, доступ к воде/электричеству, перемещение населения
3. ЭКОНОМИЧЕСКИЕ ПОСЛЕДСТВИЯ - санкции, инфляция, цены на товары, влияние на рынок труда и энергетику
4. ПОЛИТИЧЕСКИЕ РЕШЕНИЯ - внутренние законы, международные соглашения, мобилизация, дипломатические шаги
5. ИНФОРМАЦИОННО-СОЦИАЛЬНЫЕ АСПЕКТЫ - дезинформация, пропаганда, общественные протесты, настроения населения

Заголовок: {title}

Содержание: {content}

Ответь в формате:
РЕЛЕВАНТНОСТЬ: [ДА/НЕТ]
УВЕРЕННОСТЬ: [0-100]
КАТЕГОРИЯ: [military_operations/humanitarian_crisis/economic_consequences/political_decisions/information_social или НЕТ]
ПРИЧИНА: [краткое объяснение]"""
        
        return prompt
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """Парсит ответ AI
        
        Args:
            response (str): Ответ от AI
            
        Returns:
            Dict[str, Any]: Распарсенный результат
        """
        try:
            response = response.strip().lower()
            
            # Ищем релевантность
            is_relevant = False
            if 'релевантность: да' in response or 'relevance: yes' in response:
                is_relevant = True
            elif 'релевантность: нет' in response or 'relevance: no' in response:
                is_relevant = False
            else:
                # Пытаемся найти по ключевым словам
                if any(word in response for word in ['да', 'yes', 'релевантн', 'relevant']):
                    is_relevant = True
            
            # Ищем уверенность
            confidence = 0.5  # По умолчанию
            import re
            confidence_match = re.search(r'уверенность[:\s]*(\d+)', response)
            if not confidence_match:
                confidence_match = re.search(r'confidence[:\s]*(\d+)', response)
            
            if confidence_match:
                confidence = min(100, max(0, int(confidence_match.group(1)))) / 100.0
            
            # Ищем категорию
            category = None
            category_match = re.search(r'категория[:\s]*([a-z_]+)', response)
            if not category_match:
                category_match = re.search(r'category[:\s]*([a-z_]+)', response)
            
            if category_match:
                found_category = category_match.group(1).strip()
                valid_categories = ['military_operations', 'humanitarian_crisis', 'economic_consequences', 
                                 'political_decisions', 'information_social']
                if found_category in valid_categories:
                    category = found_category
            
            # Ищем причину
            reason = "AI-анализ завершен"
            reason_match = re.search(r'причина[:\s]*(.+?)(?:\n|$)', response)
            if not reason_match:
                reason_match = re.search(r'reason[:\s]*(.+?)(?:\n|$)', response)
            
            if reason_match:
                reason = reason_match.group(1).strip()
            
            return {
                'is_relevant': is_relevant,
                'confidence': confidence,
                'relevance_score': confidence,
                'category': category,
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге ответа AI: {e}")
            return {
                'is_relevant': False,
                'confidence': 0.0,
                'category': None,
                'reason': f'Ошибка парсинга: {str(e)}'
            }
    
    def _fallback_keyword_analysis(self, title: str, content: str) -> Dict[str, Any]:
        """Fallback анализ по ключевым словам когда AI не отвечает
        
        Args:
            title (str): Заголовок новости
            content (str): Содержание новости
            
        Returns:
            Dict[str, Any]: Результат анализа
        """
        try:
            # Объединяем заголовок и содержание для анализа
            text = f"{title} {content}".lower()
            
            # Подсчитываем совпадения по категориям
            category_scores = {}
            found_keywords = []
            
            for category, keywords in self.ukraine_keywords.items():
                score = 0
                for keyword in keywords:
                    if keyword.lower() in text:
                        score += 1
                        found_keywords.append(keyword)
                category_scores[category] = score
            
            # Определяем лучшую категорию
            best_category = max(category_scores, key=category_scores.get) if category_scores else None
            best_score = category_scores.get(best_category, 0) if best_category else 0
            
            # Определяем релевантность
            is_relevant = best_score >= 2  # Минимум 2 совпадения
            confidence = min(best_score / 10.0, 1.0)  # Нормализуем до 0-1
            
            return {
                'is_relevant': is_relevant,
                'confidence': confidence,
                'relevance_score': confidence,
                'category': best_category if is_relevant else 'other',
                'keywords_found': found_keywords[:5],  # Первые 5 найденных ключевых слов
                'reason': f'Keyword analysis: {best_score} matches in {best_category}' if is_relevant else 'Insufficient keyword matches'
            }
            
        except Exception as e:
            logger.error(f"Ошибка в fallback анализе: {e}")
            return {
                'is_relevant': False,
                'confidence': 0.0,
                'relevance_score': 0.0,
                'category': 'other',
                'keywords_found': [],
                'reason': f'Fallback analysis error: {str(e)}'
            }

# Функция для быстрого использования
def filter_ukraine_relevance(title: str, content: str, use_ai: bool = True) -> Dict[str, Any]:
    """Быстрая функция для фильтрации новостей по релевантности к Украине
    
    Args:
        title (str): Заголовок новости
        content (str): Содержание новости
        use_ai (bool): Использовать ли AI для анализа
        
    Returns:
        Dict[str, Any]: Словарь с результатами анализа релевантности
    """
    try:
        filter_instance = UkraineRelevanceFilter()
        result = filter_instance.is_ukraine_relevant(title, content, use_ai)
        return result
    except Exception as e:
        logger.error(f"Ошибка при фильтрации: {e}")
        return {
            'is_relevant': False,
            'confidence': 0.0,
            'relevance_score': 0.0,
            'category': 'other',
            'keywords_found': [],
            'reason': 'Ошибка фильтрации',
            'ai_analysis': None,
            'method': 'error'
        }

# Тестирование
if __name__ == "__main__":
    # Тестовые примеры
    test_cases = [
        {
            'title': 'Украина получила новую военную помощь от США',
            'content': 'Соединенные Штаты объявили о предоставлении Украине дополнительного пакета военной помощи.',
            'expected': True
        },
        {
            'title': 'Новый iPhone представлен Apple',
            'content': 'Компания Apple представила новую модель iPhone с улучшенными характеристиками.',
            'expected': False
        },
        {
            'title': 'Санкции против России усилены',
            'content': 'ЕС ввел новые санкции против российских компаний в связи с конфликтом в Украине.',
            'expected': True
        }
    ]
    
    try:
        filter_instance = UkraineRelevanceFilter()
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nТест {i}:")
            print(f"Заголовок: {test_case['title']}")
            
            result = filter_instance.is_ukraine_relevant(
                test_case['title'], 
                test_case['content']
            )
            
            print(f"Результат: {result['is_relevant']} (ожидалось: {test_case['expected']})")
            print(f"Уверенность: {result['confidence']:.2f}")
            print(f"Причина: {result['reason']}")
            print(f"Ключевые слова: {result['keywords_found']}")
            
    except Exception as e:
        print(f"Ошибка при тестировании: {e}")