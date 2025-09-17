import requests
import json
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from ..ai.content_classifier import ExtremistContentClassifier

class VKAnalyzer:
    """Класс для работы с API ВКонтакте и анализа контента"""
    
    def __init__(self, access_token: str, api_version: str = "5.131"):
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = "https://api.vk.com/method/"
        self.logger = logging.getLogger(__name__)
        
    def _make_request(self, method: str, params: Dict) -> Optional[Dict]:
        """Выполнение запроса к API ВКонтакте"""
        params.update({
            'access_token': self.access_token,
            'v': self.api_version
        })
        
        try:
            response = requests.get(f"{self.base_url}{method}", params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'error' in data:
                self.logger.error(f"VK API Error: {data['error']}")
                return None
                
            return data.get('response')
            
        except requests.RequestException as e:
            self.logger.error(f"Request error: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return None
    
    def search_posts(self, query: str, count: int = 100, start_time: Optional[datetime] = None) -> List[Dict]:
        """Поиск постов по ключевым словам"""
        params = {
            'q': query,
            'count': min(count, 200),  # Максимум 200 за запрос
            'sort': 2,  # Сортировка по дате
            'extended': 1
        }
        
        if start_time:
            params['start_time'] = int(start_time.timestamp())
        
        response = self._make_request('newsfeed.search', params)
        
        if not response:
            return []
            
        posts = []
        for item in response.get('items', []):
            if item.get('text'):
                post_data = {
                    'id': item.get('id'),
                    'owner_id': item.get('owner_id'),
                    'text': item.get('text'),
                    'date': datetime.fromtimestamp(item.get('date', 0)),
                    'likes': item.get('likes', {}).get('count', 0),
                    'reposts': item.get('reposts', {}).get('count', 0),
                    'comments': item.get('comments', {}).get('count', 0),
                    'views': item.get('views', {}).get('count', 0),
                    'attachments': item.get('attachments', []),
                    'source': 'vk'
                }
                posts.append(post_data)
                
        return posts
    
    def get_wall_posts(self, owner_id: str, count: int = 100, offset: int = 0) -> List[Dict]:
        """Получение постов со стены пользователя или группы"""
        params = {
            'owner_id': owner_id,
            'count': min(count, 100),
            'offset': offset,
            'extended': 1,
            'filter': 'all'
        }
        
        response = self._make_request('wall.get', params)
        
        if not response:
            return []
            
        posts = []
        for item in response.get('items', []):
            post_data = {
                'id': item.get('id'),
                'owner_id': item.get('owner_id'),
                'text': item.get('text', ''),
                'date': datetime.fromtimestamp(item.get('date', 0)),
                'likes': item.get('likes', {}).get('count', 0),
                'reposts': item.get('reposts', {}).get('count', 0),
                'comments': item.get('comments', {}).get('count', 0),
                'views': item.get('views', {}).get('count', 0),
                'attachments': item.get('attachments', []),
                'source': 'vk'
            }
            posts.append(post_data)
            
        return posts
    
    def get_comments(self, owner_id: str, post_id: str, count: int = 100) -> List[Dict]:
        """Получение комментариев к посту"""
        params = {
            'owner_id': owner_id,
            'post_id': post_id,
            'count': min(count, 100),
            'sort': 'desc',
            'extended': 1,
            'thread_items_count': 10
        }
        
        response = self._make_request('wall.getComments', params)
        
        if not response:
            return []
            
        comments = []
        for item in response.get('items', []):
            comment_data = {
                'id': item.get('id'),
                'from_id': item.get('from_id'),
                'text': item.get('text', ''),
                'date': datetime.fromtimestamp(item.get('date', 0)),
                'likes': item.get('likes', {}).get('count', 0),
                'reply_to_user': item.get('reply_to_user'),
                'reply_to_comment': item.get('reply_to_comment'),
                'attachments': item.get('attachments', []),
                'thread': item.get('thread', {}),
                'source': 'vk_comment'
            }
            comments.append(comment_data)
            
        return comments
    
    def search_groups(self, query: str, count: int = 50) -> List[Dict]:
        """Поиск групп по ключевым словам"""
        params = {
            'q': query,
            'type': 'group',
            'count': min(count, 1000),
            'sort': 6  # По количеству участников
        }
        
        response = self._make_request('groups.search', params)
        
        if not response:
            return []
            
        groups = []
        for item in response.get('items', []):
            group_data = {
                'id': item.get('id'),
                'name': item.get('name'),
                'screen_name': item.get('screen_name'),
                'description': item.get('description', ''),
                'members_count': item.get('members_count', 0),
                'type': item.get('type'),
                'is_closed': item.get('is_closed'),
                'activity': item.get('activity', ''),
                'source': 'vk_group'
            }
            groups.append(group_data)
            
        return groups
    
    def get_group_info(self, group_ids: List[str]) -> List[Dict]:
        """Получение информации о группах"""
        params = {
            'group_ids': ','.join(group_ids),
            'fields': 'members_count,activity,description,status,site,contacts'
        }
        
        response = self._make_request('groups.getById', params)
        
        if not response:
            return []
            
        return response
    
    def analyze_content_batch(self, posts: List[Dict], keywords: List[str]) -> List[Dict]:
        """Анализ контента на наличие экстремистских материалов с использованием ИИ классификатора"""
        analyzed_posts = []
        classifier = ExtremistContentClassifier()
        
        for post in posts:
            text = post.get('text', '')
            
            if not text.strip():
                # Если текста нет, помечаем как обычный контент
                analyzed_post = post.copy()
                analyzed_post.update({
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
                analyzed_posts.append(analyzed_post)
                continue
            
            # Используем облачную модель для анализа экстремистского контента
            cloud_analysis = classifier.analyze_extremism_percentage(text)
            
            # Базовый процент экстремизма из облачной модели
            base_extremism_percentage = cloud_analysis.get('extremism_percentage', 0)
            
            # Дополнительные факторы риска для социальных сетей
            social_risk_bonus = 0
            if post.get('reposts', 0) > 100:
                social_risk_bonus += 5
            if post.get('comments', 0) > 50:
                social_risk_bonus += 3
            if len(text) > 1000:
                social_risk_bonus += 2
            
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
            
            analyzed_post = post.copy()
            analyzed_post.update({
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
            
            analyzed_posts.append(analyzed_post)
        
        return analyzed_posts
    
    def get_trending_topics(self, count: int = 20) -> List[Dict]:
        """Получение трендовых тем"""
        params = {
            'count': min(count, 50)
        }
        
        response = self._make_request('trending.get', params)
        
        if not response:
            return []
            
        return response.get('items', [])
    
    def monitor_real_time(self, keywords: List[str], duration_minutes: int = 60) -> List[Dict]:
        """Мониторинг в реальном времени"""
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        all_posts = []
        
        while datetime.now() < end_time:
            for keyword in keywords:
                posts = self.search_posts(keyword, count=50)
                analyzed_posts = self.analyze_content_batch(posts, keywords)
                
                # Фильтрация только подозрительного контента
                suspicious_posts = [
                    post for post in analyzed_posts 
                    if post['risk_level'] in ['medium', 'high']
                ]
                
                all_posts.extend(suspicious_posts)
                
                # Пауза между запросами для соблюдения лимитов API
                time.sleep(1)
            
            # Пауза между циклами мониторинга
            time.sleep(30)
        
        return all_posts

# Пример использования
if __name__ == "__main__":
    # Инициализация анализатора
    vk_analyzer = VKAnalyzer(access_token="YOUR_VK_ACCESS_TOKEN")
    
    # Поиск подозрительного контента
    keywords = ['экстремизм', 'терроризм', 'радикализм']
    posts = vk_analyzer.search_posts('экстремизм', count=50)
    
    # Анализ контента
    analyzed_posts = vk_analyzer.analyze_content_batch(posts, keywords)
    
    # Вывод результатов
    for post in analyzed_posts:
        if post['risk_level'] in ['medium', 'high']:
            print(f"Риск: {post['risk_level']}, Текст: {post['text'][:100]}...")