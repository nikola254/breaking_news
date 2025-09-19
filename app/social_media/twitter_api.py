import requests
import json
import time
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import logging
import re
from ..ai.content_classifier import ExtremistContentClassifier

class TwitterAnalyzer:
    """Класс для работы с Twitter API v2 и анализа маргинальных аккаунтов"""
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.base_url = "https://api.twitter.com/2"
        self.logger = logging.getLogger(__name__)
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json"
        }
        
        # Ключевые слова для выявления пропагандистского контента
        self.propaganda_keywords = [
            'пропаганда', 'дезинформация', 'фейк', 'ложь', 'манипуляция',
            'враг народа', 'предатель', 'агент', 'шпион', 'диверсант',
            'экстремизм', 'терроризм', 'радикализм', 'национализм',
            'ненависть', 'вражда', 'конфликт', 'война', 'агрессия',
            'революция', 'переворот', 'свержение', 'восстание'
        ]
        
        # Паттерны для выявления маргинальных аккаунтов
        self.marginal_patterns = [
            r'патриот\d+', r'правда\d+', r'народ\d+', r'свобода\d+',
            r'борец\d+', r'защитник\d+', r'воин\d+', r'герой\d+'
        ]
        
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Выполнение запроса к Twitter API v2"""
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 429:  # Rate limit
                self.logger.warning("Rate limit reached, waiting...")
                time.sleep(900)  # Ждем 15 минут
                return self._make_request(endpoint, params)
            
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            self.logger.error(f"Twitter API request error: {e}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            return None
    
    def search_tweets(self, query: str, max_results: int = 100, 
                     start_time: Optional[datetime] = None) -> List[Dict]:
        """Поиск твитов по запросу"""
        params = {
            'query': query,
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,author_id,public_metrics,context_annotations,lang,possibly_sensitive',
            'user.fields': 'created_at,description,public_metrics,verified,location',
            'expansions': 'author_id'
        }
        
        if start_time:
            params['start_time'] = start_time.isoformat()
        
        response = self._make_request("tweets/search/recent", params)
        if not response or 'data' not in response:
            return []
        
        tweets = response['data']
        users = {user['id']: user for user in response.get('includes', {}).get('users', [])}
        
        # Обогащаем твиты информацией о пользователях
        enriched_tweets = []
        for tweet in tweets:
            user_info = users.get(tweet['author_id'], {})
            tweet['user'] = user_info
            enriched_tweets.append(tweet)
        
        return enriched_tweets
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """Получение информации о пользователе"""
        params = {
            'user.fields': 'created_at,description,public_metrics,verified,location,profile_image_url'
        }
        
        response = self._make_request(f"users/by/username/{username}", params)
        return response.get('data') if response else None
    
    def get_user_tweets(self, user_id: str, max_results: int = 100) -> List[Dict]:
        """Получение твитов пользователя"""
        params = {
            'max_results': min(max_results, 100),
            'tweet.fields': 'created_at,public_metrics,context_annotations,lang,possibly_sensitive'
        }
        
        response = self._make_request(f"users/{user_id}/tweets", params)
        return response.get('data', []) if response else []
    
    def analyze_marginal_account(self, user_info: Dict, user_tweets: List[Dict]) -> Dict:
        """Анализ аккаунта на предмет маргинальности"""
        score = 0
        indicators = []
        
        # Анализ профиля
        username = user_info.get('username', '').lower()
        description = user_info.get('description', '').lower()
        
        # Проверка паттернов в имени пользователя
        for pattern in self.marginal_patterns:
            if re.search(pattern, username):
                score += 20
                indicators.append(f"Подозрительный паттерн в имени: {pattern}")
        
        # Анализ описания профиля
        propaganda_words_in_desc = sum(1 for word in self.propaganda_keywords 
                                     if word in description)
        if propaganda_words_in_desc > 2:
            score += propaganda_words_in_desc * 10
            indicators.append(f"Пропагандистские слова в описании: {propaganda_words_in_desc}")
        
        # Анализ метрик аккаунта
        metrics = user_info.get('public_metrics', {})
        followers = metrics.get('followers_count', 0)
        following = metrics.get('following_count', 0)
        tweets_count = metrics.get('tweet_count', 0)
        
        # Подозрительные соотношения
        if following > 0 and followers / following < 0.1:  # Мало подписчиков относительно подписок
            score += 15
            indicators.append("Низкое соотношение подписчиков к подпискам")
        
        if tweets_count > 1000 and followers < 100:  # Много твитов, мало подписчиков
            score += 25
            indicators.append("Высокая активность при малом количестве подписчиков")
        
        # Анализ контента твитов
        if user_tweets:
            propaganda_tweets = 0
            total_engagement = 0
            
            for tweet in user_tweets:
                text = tweet.get('text', '').lower()
                
                # Подсчет пропагандистских слов
                propaganda_words = sum(1 for word in self.propaganda_keywords if word in text)
                if propaganda_words > 1:
                    propaganda_tweets += 1
                
                # Анализ вовлеченности
                tweet_metrics = tweet.get('public_metrics', {})
                engagement = (tweet_metrics.get('like_count', 0) + 
                            tweet_metrics.get('retweet_count', 0) + 
                            tweet_metrics.get('reply_count', 0))
                total_engagement += engagement
            
            propaganda_ratio = propaganda_tweets / len(user_tweets)
            if propaganda_ratio > 0.3:  # Более 30% твитов содержат пропаганду
                score += int(propaganda_ratio * 50)
                indicators.append(f"Высокий процент пропагандистских твитов: {propaganda_ratio:.2%}")
            
            avg_engagement = total_engagement / len(user_tweets) if user_tweets else 0
            if avg_engagement < 1 and len(user_tweets) > 50:  # Низкая вовлеченность при высокой активности
                score += 20
                indicators.append("Низкая вовлеченность при высокой активности")
        
        # Определение уровня риска
        if score >= 80:
            risk_level = "high"
        elif score >= 50:
            risk_level = "medium"
        elif score >= 20:
            risk_level = "low"
        else:
            risk_level = "minimal"
        
        return {
            'user_id': user_info.get('id'),
            'username': user_info.get('username'),
            'risk_score': score,
            'risk_level': risk_level,
            'indicators': indicators,
            'analysis_date': datetime.now().isoformat(),
            'user_metrics': metrics,
            'tweets_analyzed': len(user_tweets)
        }
    
    def find_marginal_accounts(self, search_queries: List[str], 
                             max_accounts: int = 50) -> List[Dict]:
        """Поиск маргинальных аккаунтов по ключевым запросам"""
        marginal_accounts = []
        processed_users = set()
        
        for query in search_queries:
            self.logger.info(f"Searching for query: {query}")
            tweets = self.search_tweets(query, max_results=100)
            
            for tweet in tweets:
                user_info = tweet.get('user', {})
                user_id = user_info.get('id')
                
                if user_id and user_id not in processed_users:
                    processed_users.add(user_id)
                    
                    # Получаем твиты пользователя
                    user_tweets = self.get_user_tweets(user_id, max_results=50)
                    
                    # Анализируем аккаунт
                    analysis = self.analyze_marginal_account(user_info, user_tweets)
                    
                    # Добавляем только аккаунты с риском выше минимального
                    if analysis['risk_level'] != 'minimal':
                        marginal_accounts.append(analysis)
                        self.logger.info(f"Found marginal account: {analysis['username']} "
                                       f"(risk: {analysis['risk_level']})")
                    
                    if len(marginal_accounts) >= max_accounts:
                        break
                
                # Пауза между запросами для соблюдения лимитов
                time.sleep(1)
            
            if len(marginal_accounts) >= max_accounts:
                break
        
        # Сортируем по уровню риска
        marginal_accounts.sort(key=lambda x: x['risk_score'], reverse=True)
        return marginal_accounts
    
    def extract_propaganda_content(self, marginal_accounts: List[Dict]) -> List[Dict]:
        """Извлечение пропагандистского контента из маргинальных аккаунтов"""
        propaganda_content = []
        
        for account in marginal_accounts:
            if account['risk_level'] in ['medium', 'high']:
                user_id = account['user_id']
                username = account['username']
                
                # Получаем последние твиты
                tweets = self.get_user_tweets(user_id, max_results=100)
                
                for tweet in tweets:
                    text = tweet.get('text', '').lower()
                    
                    # Проверяем на наличие пропагандистских слов
                    propaganda_words = [word for word in self.propaganda_keywords if word in text]
                    
                    if len(propaganda_words) > 1:  # Минимум 2 пропагандистских слова
                        content_item = {
                            'tweet_id': tweet.get('id'),
                            'user_id': user_id,
                            'username': username,
                            'text': tweet.get('text'),
                            'created_at': tweet.get('created_at'),
                            'propaganda_keywords': propaganda_words,
                            'public_metrics': tweet.get('public_metrics', {}),
                            'risk_level': account['risk_level'],
                            'extracted_at': datetime.now().isoformat()
                        }
                        propaganda_content.append(content_item)
                
                # Пауза между пользователями
                time.sleep(2)
        
        return propaganda_content
    
    def monitor_accounts(self, account_usernames: List[str], 
                        duration_hours: int = 24) -> List[Dict]:
        """Мониторинг активности маргинальных аккаунтов"""
        monitoring_results = []
        end_time = datetime.now() + timedelta(hours=duration_hours)
        
        while datetime.now() < end_time:
            for username in account_usernames:
                user_info = self.get_user_info(username)
                if user_info:
                    user_tweets = self.get_user_tweets(user_info['id'], max_results=10)
                    
                    # Анализируем новые твиты
                    for tweet in user_tweets:
                        created_at = datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00'))
                        if created_at > datetime.now() - timedelta(hours=1):  # Твиты за последний час
                            text = tweet.get('text', '').lower()
                            propaganda_words = [word for word in self.propaganda_keywords if word in text]
                            
                            if propaganda_words:
                                monitoring_results.append({
                                    'username': username,
                                    'tweet_id': tweet.get('id'),
                                    'text': tweet.get('text'),
                                    'created_at': tweet.get('created_at'),
                                    'propaganda_keywords': propaganda_words,
                                    'detected_at': datetime.now().isoformat()
                                })
                
                time.sleep(5)  # Пауза между пользователями
            
            # Пауза между циклами мониторинга
            time.sleep(300)  # 5 минут
        
        return monitoring_results

if __name__ == "__main__":
    # Пример использования
    from config import Config
    
    if Config.TWITTER_BEARER_TOKEN:
        twitter_analyzer = TwitterAnalyzer(Config.TWITTER_BEARER_TOKEN)
        
        # Поиск маргинальных аккаунтов
        search_queries = [
            'пропаганда', 'дезинформация', 'враг народа', 
            'предатель родины', 'агент запада'
        ]
        
        marginal_accounts = twitter_analyzer.find_marginal_accounts(search_queries, max_accounts=20)
        
        print(f"Найдено маргинальных аккаунтов: {len(marginal_accounts)}")
        for account in marginal_accounts[:5]:  # Показываем топ-5
            print(f"@{account['username']} - Риск: {account['risk_level']} "
                  f"(Счет: {account['risk_score']})")
        
        # Извлечение пропагандистского контента
        propaganda_content = twitter_analyzer.extract_propaganda_content(marginal_accounts)
        print(f"Извлечено пропагандистских твитов: {len(propaganda_content)}")
    else:
        print("Twitter Bearer Token не настроен в конфигурации")