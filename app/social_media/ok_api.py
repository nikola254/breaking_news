import requests
import json
import hashlib
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from ..ai.content_classifier import ExtremistContentClassifier

class OKAnalyzer:
    """Класс для работы с API Одноклассников и анализа контента"""
    
    def __init__(self, application_id: str, application_key: str, access_token: str, session_secret_key: str):
        self.application_id = application_id
        self.application_key = application_key
        self.access_token = access_token
        self.session_secret_key = session_secret_key
        self.base_url = "https://api.ok.ru/fb.do"
        self.logger = logging.getLogger(__name__)
        
    def _generate_signature(self, params: Dict) -> str:
        """Генерация подписи для запроса к API OK"""
        try:
            # Проверяем входные параметры
            if not params or not isinstance(params, dict):
                params = {}
            
            # Сортируем параметры по ключу, фильтруя None значения
            filtered_params = {k: v for k, v in params.items() if v is not None}
            sorted_params = sorted(filtered_params.items())
            
            # Создаем строку параметров с проверкой на None
            param_parts = []
            for key, value in sorted_params:
                if key is not None and value is not None:
                    param_parts.append(f"{key}={value}")
            
            param_string = ''.join(param_parts)
            
            # Проверяем секретный ключ
            if not self.session_secret_key:
                raise ValueError("session_secret_key не может быть пустым")
            
            # Добавляем секретный ключ
            param_string += str(self.session_secret_key)
            
            # Проверяем, что строка не пустая
            if not param_string:
                param_string = str(self.session_secret_key)
            
            # Вычисляем MD5 хеш
            signature = hashlib.md5(param_string.encode('utf-8')).hexdigest()
            
            return signature
            
        except Exception as e:
            self.logger.error(f"Ошибка при генерации подписи: {e}")
            # Возвращаем базовую подпись из секретного ключа
            return hashlib.md5(str(self.session_secret_key).encode('utf-8')).hexdigest()
    
    def _make_request(self, method: str, params: Dict) -> Optional[Dict]:
        """Выполнение запроса к API Одноклассников"""
        try:
            # Проверяем входные параметры
            if not method:
                self.logger.error("Метод API не может быть пустым")
                return None
            
            if not params or not isinstance(params, dict):
                params = {}
            
            # Проверяем обязательные параметры
            if not self.application_key:
                self.logger.error("application_key не установлен")
                return None
            
            if not self.access_token:
                self.logger.error("access_token не установлен")
                return None
            
            # Добавляем обязательные параметры с проверкой на None
            params.update({
                'application_key': str(self.application_key) if self.application_key else '',
                'access_token': str(self.access_token) if self.access_token else '',
                'method': str(method) if method else '',
                'format': 'json'
            })
            
            # Генерируем подпись
            signature = self._generate_signature(params)
            if not signature:
                self.logger.error("Не удалось сгенерировать подпись")
                return None
            
            params['sig'] = signature
            
            response = requests.post(self.base_url, data=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'error_code' in data:
                self.logger.error(f"OK API Error: {data}")
                return None
                
            return data
            
        except requests.RequestException as e:
            self.logger.error(f"Request error: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error in _make_request: {e}")
            return None
    
    def search_groups(self, query: str, count: int = 50) -> List[Dict]:
        """Поиск групп по ключевым словам"""
        params = {
            'query': query,
            'count': min(count, 100)
        }
        
        response = self._make_request('group.search', params)
        
        if not response:
            return []
            
        groups = []
        for group in response.get('groups', []):
            group_data = {
                'id': group.get('uid'),
                'name': group.get('name'),
                'description': group.get('description', ''),
                'members_count': group.get('members_count', 0),
                'photo_url': group.get('pic_1'),
                'shortname': group.get('shortname'),
                'private': group.get('private', False),
                'source': 'ok_group'
            }
            groups.append(group_data)
            
        return groups
    
    def get_group_info(self, group_id: str) -> Optional[Dict]:
        """Получение информации о группе"""
        params = {
            'uids': group_id,
            'fields': 'uid,name,description,shortname,pic_1,members_count,private'
        }
        
        response = self._make_request('group.getInfo', params)
        
        if not response:
            return None
            
        groups = response.get('groups', [])
        if groups:
            group = groups[0]
            return {
                'id': group.get('uid'),
                'name': group.get('name'),
                'description': group.get('description', ''),
                'members_count': group.get('members_count', 0),
                'photo_url': group.get('pic_1'),
                'shortname': group.get('shortname'),
                'private': group.get('private', False),
                'source': 'ok_group'
            }
        
        return None
    
    def get_group_topics(self, group_id: str, count: int = 50) -> List[Dict]:
        """Получение тем группы"""
        params = {
            'gid': group_id,
            'count': min(count, 100),
            'fields': 'topic.id,topic.text,topic.created_ms,topic.ref_objects'
        }
        
        response = self._make_request('group.getTopics', params)
        
        if not response:
            return []
            
        topics = []
        for topic in response.get('topics', []):
            topic_data = {
                'id': topic.get('id'),
                'text': topic.get('text', ''),
                'created_date': datetime.fromtimestamp(topic.get('created_ms', 0) / 1000),
                'author_id': topic.get('author_id'),
                'group_id': group_id,
                'likes_count': topic.get('like_count', 0),
                'comments_count': topic.get('discussion_summary', {}).get('comments_count', 0),
                'attachments': topic.get('attachments', []),
                'source': 'ok_topic'
            }
            topics.append(topic_data)
            
        return topics
    
    def get_topic_comments(self, topic_id: str, count: int = 100) -> List[Dict]:
        """Получение комментариев к теме"""
        params = {
            'topic_id': topic_id,
            'count': min(count, 100)
        }
        
        response = self._make_request('discussions.get', params)
        
        if not response:
            return []
            
        comments = []
        for comment in response.get('comments', []):
            comment_data = {
                'id': comment.get('id'),
                'text': comment.get('text', ''),
                'created_date': datetime.fromtimestamp(comment.get('created_ms', 0) / 1000),
                'author_id': comment.get('author_id'),
                'topic_id': topic_id,
                'likes_count': comment.get('like_count', 0),
                'attachments': comment.get('attachments', []),
                'source': 'ok_comment'
            }
            comments.append(comment_data)
            
        return comments
    
    def search_users(self, query: str, count: int = 50) -> List[Dict]:
        """Поиск пользователей"""
        params = {
            'query': query,
            'count': min(count, 100)
        }
        
        response = self._make_request('users.search', params)
        
        if not response:
            return []
            
        users = []
        for user in response.get('users', []):
            user_data = {
                'id': user.get('uid'),
                'name': f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                'photo_url': user.get('pic_1'),
                'online': user.get('online'),
                'location': user.get('location', {}).get('city'),
                'source': 'ok_user'
            }
            users.append(user_data)
            
        return users
    
    def get_user_activity(self, user_id: str, count: int = 50) -> List[Dict]:
        """Получение активности пользователя"""
        params = {
            'uid': user_id,
            'count': min(count, 100)
        }
        
        response = self._make_request('stream.get', params)
        
        if not response:
            return []
            
        activities = []
        for activity in response.get('stream', []):
            activity_data = {
                'id': activity.get('id'),
                'text': activity.get('text', ''),
                'created_date': datetime.fromtimestamp(activity.get('created_ms', 0) / 1000),
                'author_id': activity.get('author_id'),
                'type': activity.get('type'),
                'likes_count': activity.get('like_count', 0),
                'comments_count': activity.get('comments_count', 0),
                'attachments': activity.get('attachments', []),
                'source': 'ok_activity'
            }
            activities.append(activity_data)
            
        return activities
    
    def analyze_content_batch(self, content_items: List[Dict], keywords: List[str]) -> List[Dict]:
        """Анализ контента на наличие экстремистских материалов с использованием ИИ классификатора"""
        analyzed_items = []
        classifier = ExtremistContentClassifier()
        
        for item in content_items:
            text = item.get('text', '')
            
            if not text.strip():
                # Если текста нет, помечаем как обычный контент
                analyzed_item = item.copy()
                analyzed_item.update({
                    'classification': 'normal',
                    'confidence': 0.1,
                    'risk_score': 0,
                    'risk_level': 'none',
                    'extremism_percentage': 0,
                    'found_keywords': [],
                    'highlighted_text': text,
                    'threat_color': '#28a745',
                    'detected_keywords': [],
                    'analysis_date': datetime.now(),
                    'analysis_method': 'empty_content'
                })
                analyzed_items.append(analyzed_item)
                continue
            
            # Используем облачную модель для анализа экстремистского контента
            cloud_analysis = classifier.analyze_extremism_percentage(text)
            
            # Базовый процент экстремизма из облачной модели
            base_extremism_percentage = cloud_analysis.get('extremism_percentage', 0)
            
            # Дополнительные факторы риска для Одноклассников
            social_risk_bonus = 0
            if item.get('likes_count', 0) > 50:
                social_risk_bonus += 3
            if item.get('comments_count', 0) > 20:
                social_risk_bonus += 2
            if len(text) > 500:
                social_risk_bonus += 2
            
            # Проверка на наличие подозрительных вложений
            attachments = item.get('attachments', [])
            if attachments:
                for attachment in attachments:
                    if attachment.get('type') in ['video', 'doc']:
                        social_risk_bonus += 3
                        break
            
            # Корректируем процент экстремизма с учетом социальных факторов
            adjusted_extremism_percentage = min(100, base_extremism_percentage + social_risk_bonus)
            
            # Определяем уровень риска на основе процента экстремизма
            if adjusted_extremism_percentage >= 80:
                risk_level = 'critical'
            elif adjusted_extremism_percentage >= 60:
                risk_level = 'high'
            elif adjusted_extremism_percentage >= 40:
                risk_level = 'medium'
            elif adjusted_extremism_percentage >= 20:
                risk_level = 'low'
            else:
                risk_level = 'none'
            
            analyzed_item = item.copy()
            analyzed_item.update({
                'classification': 'extremist' if adjusted_extremism_percentage >= 40 else ('suspicious' if adjusted_extremism_percentage >= 20 else 'normal'),
                'confidence': cloud_analysis.get('confidence', 0),
                'risk_score': adjusted_extremism_percentage,
                'risk_level': risk_level,
                'extremism_percentage': adjusted_extremism_percentage,
                'found_keywords': cloud_analysis.get('detected_keywords', []),
                'highlighted_text': text,  # Можно добавить выделение ключевых слов
                'threat_color': '#dc3545' if risk_level == 'critical' else ('#fd7e14' if risk_level == 'high' else ('#ffc107' if risk_level == 'medium' else ('#28a745' if risk_level == 'none' else '#6c757d'))),
                'detected_keywords': cloud_analysis.get('detected_keywords', []),
                'analysis_date': datetime.now(),
                'analysis_method': cloud_analysis.get('method', 'cloud_api'),
                'explanation': cloud_analysis.get('explanation', ''),
                'social_risk_bonus': social_risk_bonus,
                # Информация облачного анализа
                'cloud_percentage': cloud_analysis.get('extremism_percentage', 0),
                'base_percentage': base_extremism_percentage
            })
            
            analyzed_items.append(analyzed_item)
        
        return analyzed_items
    
    def monitor_groups(self, group_ids: List[str], keywords: List[str]) -> List[Dict]:
        """Мониторинг групп на предмет экстремистского контента"""
        all_content = []
        
        for group_id in group_ids:
            try:
                # Получаем темы группы
                topics = self.get_group_topics(group_id, count=50)
                
                for topic in topics:
                    # Получаем комментарии к теме
                    comments = self.get_topic_comments(topic['id'], count=50)
                    
                    # Анализируем тему
                    analyzed_topics = self.analyze_content_batch([topic], keywords)
                    all_content.extend(analyzed_topics)
                    
                    # Анализируем комментарии
                    analyzed_comments = self.analyze_content_batch(comments, keywords)
                    all_content.extend(analyzed_comments)
                    
                    # Пауза между запросами
                    time.sleep(0.5)
                    
            except Exception as e:
                self.logger.error(f"Error monitoring group {group_id}: {e}")
                continue
        
        # Фильтруем только подозрительный контент
        suspicious_content = [
            item for item in all_content 
            if item['risk_level'] in ['medium', 'high']
        ]
        
        return suspicious_content
    
    def get_trending_content(self, keywords: List[str]) -> List[Dict]:
        """Получение трендового контента по ключевым словам"""
        all_content = []
        
        for keyword in keywords:
            # Поиск групп по ключевому слову
            groups = self.search_groups(keyword, count=20)
            
            for group in groups:
                try:
                    # Получаем последние темы группы
                    topics = self.get_group_topics(group['id'], count=10)
                    analyzed_topics = self.analyze_content_batch(topics, keywords)
                    all_content.extend(analyzed_topics)
                    
                    time.sleep(0.5)
                    
                except Exception as e:
                    self.logger.error(f"Error getting content from group {group['id']}: {e}")
                    continue
        
        # Сортируем по уровню риска и дате
        all_content.sort(key=lambda x: (x['risk_score'], x.get('created_date', datetime.min)), reverse=True)
        
        return all_content[:100]  # Возвращаем топ-100

# Пример использования
if __name__ == "__main__":
    # Инициализация анализатора
    ok_analyzer = OKAnalyzer(
        application_id="YOUR_APP_ID",
        application_key="YOUR_APP_KEY",
        access_token="YOUR_ACCESS_TOKEN",
        session_secret_key="YOUR_SESSION_SECRET"
    )
    
    # Поиск подозрительного контента
    keywords = ['экстремизм', 'терроризм', 'радикализм']
    
    # Поиск групп
    groups = ok_analyzer.search_groups('политика', count=10)
    
    # Мониторинг найденных групп
    group_ids = [group['id'] for group in groups]
    suspicious_content = ok_analyzer.monitor_groups(group_ids, keywords)
    
    # Вывод результатов
    for content in suspicious_content:
        if content['risk_level'] in ['medium', 'high']:
            print(f"Риск: {content['risk_level']}, Источник: {content['source']}, Текст: {content['text'][:100]}...")