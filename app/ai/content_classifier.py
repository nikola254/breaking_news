import re
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import logging
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os
from unittest.mock import patch, Mock
from config import Config


class ExtremistContentClassifier:
    """Система классификации экстремистского контента с использованием машинного обучения"""
    
    def __init__(self, model_path: str = None):
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            ngram_range=(1, 3),
            stop_words=self._get_russian_stop_words(),
            lowercase=True,
            strip_accents='unicode'
        )
        
        self.models = {
            'naive_bayes': MultinomialNB(),
            'logistic_regression': LogisticRegression(random_state=42, max_iter=1000),
            'random_forest': RandomForestClassifier(n_estimators=100, random_state=42)
        }
        
        self.best_model = None
        self.model_path = model_path
        self.logger = logging.getLogger(__name__)
        
        # Словари для анализа
        self.extremist_keywords = self._load_extremist_keywords()
        self.hate_speech_patterns = self._load_hate_speech_patterns()
        self.threat_patterns = self._load_threat_patterns()
        
        # Инициализация облачной модели из config.py
        self.cloud_model_url = Config.CLOUD_MODEL_URL
        self.cloud_model_token = Config.CLOUD_MODEL_TOKEN
        
        # Логируем статус конфигурации
        if self.cloud_model_url and self.cloud_model_token:
            self.logger.info("Cloud model configured successfully")
        else:
            self.logger.warning("Cloud model not configured - using local analysis only")
        
    def _get_russian_stop_words(self) -> List[str]:
        """Получение списка стоп-слов для русского языка"""
        return [
            'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так',
            'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было',
            'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему', 'теперь', 'когда', 'даже', 'ну', 'вдруг',
            'ли', 'если', 'уже', 'или', 'ни', 'быть', 'был', 'него', 'до', 'вас', 'нибудь', 'опять', 'уж',
            'вам', 'ведь', 'там', 'потом', 'себя', 'ничего', 'ей', 'может', 'они', 'тут', 'где', 'есть',
            'надо', 'ней', 'для', 'мы', 'тебя', 'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего',
            'раз', 'тоже', 'себе', 'под', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого',
            'какой', 'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее',
            'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 'наконец', 'два', 'об',
            'другой', 'хоть', 'после', 'над', 'больше', 'тот', 'через', 'эти', 'нас', 'про', 'всего',
            'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя', 'впрочем', 'хорошо', 'свою', 'этой',
            'перед', 'иногда', 'лучше', 'чуть', 'том', 'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно',
            'всю', 'между'
        ]
    
    def _load_extremist_keywords(self) -> Dict[str, List[str]]:
        """Загрузка ключевых слов экстремистского контента с улучшенной точностью"""
        return {
            'terrorism': [
                'терроризм', 'террорист', 'теракт', 'смертник', 'джихад', 
                'шахид', 'мученик', 'священная война', 'взрывчатка', 'самоподрыв'
            ],
            'extremism': [
                'экстремизм', 'экстремист', 'радикализм', 'фанатик',
                'фундаментализм', 'сепаратизм', 'сепаратист', 'радикализация'
            ],
            'hate_speech': [
                'фашизм', 'фашист', 'нацизм', 'нацист', 'расизм', 'расист',
                'ксенофобия', 'антисемитизм', 'шовинизм', 'геноцид', 'этническая чистка'
            ],
            'violence': [
                'убийство', 'убить', 'убью', 'расстрел', 'расстрелять',
                'казнь', 'казнить', 'пытка', 'пытать', 'зарезать', 'зарежу'
            ],
            'weapons': [
                'автомат калашникова', 'ак-47', 'пистолет', 'винтовка', 'граната',
                'взрывчатое вещество', 'тротил', 'самодельная бомба', 'снайперская винтовка'
            ],
            'calls_to_action': [
                'свержение власти', 'свергнуть правительство', 'захват власти', 
                'государственный переворот', 'вооруженное восстание', 'призыв к насилию'
            ]
        }
    
    def _load_hate_speech_patterns(self) -> List[str]:
        """Загрузка паттернов языка вражды"""
        return [
            r'\b(?:убить|убью|убьем)\s+(?:всех|их)\b',
            r'\b(?:смерть|смерти)\s+(?:врагам|предателям|изменникам)\b',
            r'\b(?:уничтожить|уничтожим)\s+(?:всех|их)\b',
            r'\b(?:кровь|кровью)\s+(?:за|отомстим)\b',
            r'\b(?:месть|мщение)\s+(?:за|будет)\b',
            r'\b(?:война|войну)\s+(?:до|победного)\b',
            r'\b(?:враг|враги)\s+(?:должны|будут)\s+(?:умереть|погибнуть)\b'
        ]
    
    def _load_threat_patterns(self) -> List[str]:
        """Загрузка паттернов угроз"""
        return [
            r'\b(?:я|мы)\s+(?:убью|убьем|взорву|взорвем)\b',
            r'\b(?:готовлю|готовим)\s+(?:теракт|взрыв|атаку)\b',
            r'\b(?:скоро|завтра|сегодня)\s+(?:будет|произойдет)\s+(?:взрыв|теракт)\b',
            r'\b(?:заложу|заложим)\s+(?:бомбу|взрывчатку)\b',
            r'\b(?:расстреляю|расстреляем)\s+(?:всех|их)\b'
        ]
    
    def extract_features(self, text: str) -> Dict[str, float]:
        """Извлечение признаков из текста"""
        features = {}
        text_lower = text.lower()
        
        # Подсчет ключевых слов по категориям с использованием границ слов
        for category, keywords in self.extremist_keywords.items():
            count = 0
            for keyword in keywords:
                # Используем регулярные выражения с границами слов для точного поиска
                pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = re.findall(pattern, text_lower)
                count += len(matches)
            features[f'{category}_count'] = count
            features[f'{category}_density'] = count / len(text.split()) if text.split() else 0
        
        # Поиск паттернов языка вражды
        hate_speech_matches = 0
        for pattern in self.hate_speech_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                hate_speech_matches += 1
        features['hate_speech_patterns'] = hate_speech_matches
        
        # Поиск паттернов угроз
        threat_matches = 0
        for pattern in self.threat_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                threat_matches += 1
        features['threat_patterns'] = threat_matches
        
        # Дополнительные признаки
        features['text_length'] = len(text)
        features['word_count'] = len(text.split())
        features['exclamation_count'] = text.count('!')
        features['question_count'] = text.count('?')
        features['caps_ratio'] = sum(1 for c in text if c.isupper()) / len(text) if text else 0
        
        # Эмоциональная окраска
        emotional_words = ['ярость', 'гнев', 'ненависть', 'злость', 'бешенство', 'ужас', 'страх']
        features['emotional_words'] = sum(1 for word in emotional_words if word in text_lower)
        
        return features
    
    def analyze_text_rule_based(self, text: str) -> Dict[str, any]:
        """Анализ текста на основе правил с улучшенной логикой"""
        features = self.extract_features(text)
        
        # Подсчет общего риска с более точными весами
        risk_score = 0
        risk_factors = []
        found_keywords = []
        
        # Проверка ключевых слов с разными весами для разных категорий
        category_weights = {
            'terrorism': 8,      # Самый высокий вес
            'threat_patterns': 10,
            'violence': 6,
            'weapons': 5,
            'extremism': 4,
            'hate_speech': 3,
            'calls_to_action': 3
        }
        
        for category, count in features.items():
            if category.endswith('_count') and count > 0:
                category_name = category.replace('_count', '')
                weight = category_weights.get(category_name, 2)
                risk_score += count * weight
                risk_factors.append(f"{category_name}: {count}")
                
                # Собираем найденные ключевые слова для выделения
                if category_name in self.extremist_keywords:
                    for keyword in self.extremist_keywords[category_name]:
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        if re.search(pattern, text.lower()):
                            found_keywords.append(keyword)
        
        # Проверка паттернов с повышенным весом
        if features['hate_speech_patterns'] > 0:
            risk_score += features['hate_speech_patterns'] * 8
            risk_factors.append(f"Паттерны языка вражды: {features['hate_speech_patterns']}")
        
        if features['threat_patterns'] > 0:
            risk_score += features['threat_patterns'] * 12
            risk_factors.append(f"Паттерны угроз: {features['threat_patterns']}")
        
        # Дополнительные факторы (с меньшим весом)
        if features['caps_ratio'] > 0.5:  # Повышен порог
            risk_score += 1
            risk_factors.append("Высокий процент заглавных бувкв")
        
        if features['exclamation_count'] > 5:  # Повышен порог
            risk_score += 1
            risk_factors.append("Множественные восклицательные знаки")
        
        # Проверка на контекст новостей (снижение ложных срабатываний)
        news_context_words = ['сообщает', 'новости', 'по данным', 'источник', 'корреспондент', 
                             'агентство', 'пресс-служба', 'официально', 'заявил', 'сообщил']
        has_news_context = any(word in text.lower() for word in news_context_words)
        
        if has_news_context and risk_score < 15:
            risk_score = max(0, risk_score - 3)  # Снижаем риск для новостного контекста
            risk_factors.append("Новостной контекст (снижение риска)")
        
        # Более строгое определение уровня риска
        if risk_score >= 25:
            risk_level = 'critical'
        elif risk_score >= 15:
            risk_level = 'high'
        elif risk_score >= 8:
            risk_level = 'medium'
        elif risk_score >= 3:
            risk_level = 'low'
        else:
            risk_level = 'none'
        
        return {
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'found_keywords': found_keywords,
            'features': features,
            'analysis_method': 'rule_based',
            'analysis_date': datetime.now()
        }
    
    def train_models(self, texts: List[str], labels: List[int]) -> Dict[str, float]:
        """Обучение моделей машинного обучения"""
        # Векторизация текстов
        X = self.vectorizer.fit_transform(texts)
        y = np.array(labels)
        
        # Разделение на обучающую и тестовую выборки
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        results = {}
        
        # Обучение и оценка каждой модели
        for name, model in self.models.items():
            self.logger.info(f"Training {name}...")
            
            # Обучение
            model.fit(X_train, y_train)
            
            # Предсказание
            y_pred = model.predict(X_test)
            
            # Оценка
            accuracy = accuracy_score(y_test, y_pred)
            results[name] = accuracy
            
            self.logger.info(f"{name} accuracy: {accuracy:.4f}")
            print(f"\n{name} Classification Report:")
            print(classification_report(y_test, y_pred))
        
        # Выбор лучшей модели
        best_model_name = max(results, key=results.get)
        self.best_model = self.models[best_model_name]
        
        self.logger.info(f"Best model: {best_model_name} with accuracy: {results[best_model_name]:.4f}")
        
        return results
    
    def predict_ml(self, text: str) -> Dict[str, any]:
        """Предсказание с использованием обученной модели"""
        if self.best_model is None:
            raise Exception("Model not trained. Call train_models() first.")
        
        # Векторизация текста
        X = self.vectorizer.transform([text])
        
        # Предсказание
        prediction = self.best_model.predict(X)[0]
        probability = self.best_model.predict_proba(X)[0] if hasattr(self.best_model, 'predict_proba') else None
        
        # Определение уровня риска на основе предсказания
        if prediction == 1:
            if probability is not None and probability[1] > 0.8:
                risk_level = 'high'
            elif probability is not None and probability[1] > 0.6:
                risk_level = 'medium'
            else:
                risk_level = 'low'
        else:
            risk_level = 'none'
        
        return {
            'prediction': int(prediction),
            'probability': probability[1] if probability is not None else None,
            'risk_level': risk_level,
            'analysis_method': 'machine_learning',
            'analysis_date': datetime.now()
        }
    
    def predict_cloud_model(self, text: str) -> Dict:
        """Отправка текста в облачную модель для анализа"""
        if not self.cloud_model_url or not self.cloud_model_token:
            self.logger.warning("Cloud model not configured")
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.cloud_model_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'Qwen/Qwen3-Coder-480B-A35B-Instruct',
                'max_tokens': 1000,
                'temperature': 0.3,
                'messages': [
                    {
                        'role': 'user',
                        'content': f'Проанализируй следующий текст на наличие экстремистского контента и верни только JSON с полями: extremism_percentage (число от 0 до 100), risk_level (none/low/medium/high/critical), detected_keywords (массив найденных ключевых слов), explanation (краткое объяснение). Текст: {text}'
                    }
                ]
            }
            
            response = requests.post(self.cloud_model_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Парсим JSON ответ
            try:
                import json
                analysis = json.loads(content)
                return analysis
            except json.JSONDecodeError:
                # Если не удалось распарсить JSON, создаем базовый ответ
                return {
                    'extremism_percentage': 0,
                    'risk_level': 'none',
                    'detected_keywords': [],
                    'explanation': 'Ошибка парсинга ответа модели'
                }
            
        except requests.RequestException as e:
            self.logger.error(f"Cloud model request error: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Cloud model error: {e}")
            return None

    def analyze_extremism_percentage(self, text: str) -> Dict:
        """
        Определение процента экстремизма через облачную модель API.
        
        Принцип определения:
        1. Текст отправляется в облачную модель для анализа
        2. Модель анализирует контент на наличие экстремистских признаков
        3. Возвращается процент экстремизма (0-100%) и уровень риска
        4. Учитываются ключевые слова, контекст и семантика
        """
        cloud_result = self.predict_cloud_model(text)
        
        if cloud_result:
            return {
                'extremism_percentage': cloud_result.get('extremism_percentage', 0),
                'risk_level': cloud_result.get('risk_level', 'none'),
                'detected_keywords': cloud_result.get('detected_keywords', []),
                'explanation': cloud_result.get('explanation', ''),
                'method': 'cloud_api',
                'confidence': min(100, cloud_result.get('extremism_percentage', 0)) / 100
            }
        else:
            # Fallback к локальному анализу
            local_result = self.classify_content(text)
            return {
                'extremism_percentage': int(local_result['risk_score'] * 3.33),  # Приводим к шкале 0-100
                'risk_level': local_result['risk_level'],
                'detected_keywords': local_result.get('keywords', []),
                'explanation': f"Локальный анализ: {local_result['label']}",
                'method': 'local_fallback',
                'confidence': local_result['confidence']
            }

    def analyze_text_combined(self, text: str) -> Dict[str, any]:
        """Комбинированный анализ (правила + ML + Облачная модель)"""
        # Сначала пробуем облачную модель
        cloud_result = self.predict_cloud_model(text)
        if cloud_result and cloud_result.get('label') == 'extremist':
            return {
                'risk_score': cloud_result.get('confidence', 0.9) * 30,  # Приводим к шкале risk_score
                'risk_level': 'high' if cloud_result.get('confidence', 0.9) > 0.7 else 'critical',
                'rule_based_result': None,
                'ml_result': None,
                'cloud_result': cloud_result,
                'analysis_method': 'cloud_model',
                'analysis_date': datetime.now()
            }

        # Если облачная модель недоступна или не дала результат, используем локальные методы
        rule_based_result = self.analyze_text_rule_based(text)
        
        # Если модель обучена, используем и ML
        if self.best_model is not None:
            try:
                ml_result = self.predict_ml(text)
                
                # Комбинируем результаты
                combined_risk_score = rule_based_result['risk_score']
                
                if ml_result['prediction'] == 1:
                    combined_risk_score += 10 * (ml_result['probability'] or 0.5)
                
                # Определяем финальный уровень риска
                if combined_risk_score >= 25 or ml_result['risk_level'] == 'high':
                    final_risk_level = 'critical'
                elif combined_risk_score >= 15 or ml_result['risk_level'] == 'medium':
                    final_risk_level = 'high'
                elif combined_risk_score >= 8 or ml_result['risk_level'] == 'low':
                    final_risk_level = 'medium'
                elif combined_risk_score >= 3:
                    final_risk_level = 'low'
                else:
                    final_risk_level = 'none'
                
                return {
                    'risk_score': combined_risk_score,
                    'risk_level': final_risk_level,
                    'rule_based_result': rule_based_result,
                    'ml_result': ml_result,
                    'analysis_method': 'combined',
                    'analysis_date': datetime.now()
                }
                
            except Exception as e:
                self.logger.error(f"ML prediction failed: {e}")
                return rule_based_result
        
        return rule_based_result
    
    def classify_content(self, text: str) -> Dict[str, any]:
        """Классификация контента для совместимости с существующим кодом"""
        result = self.analyze_text_combined(text)
        
        # Преобразуем результат в ожидаемый формат
        risk_level = result.get('risk_level', 'none')
        risk_score = result.get('risk_score', 0)
        
        # Вычисляем confidence на основе risk_score с улучшенной логикой
        if risk_score >= 20:
            confidence = 0.9  # Критический уровень - высокая уверенность
            label = 'extremist'
        elif risk_score >= 10:
            confidence = 0.75  # Высокий уровень
            label = 'extremist'
        elif risk_score >= 5:
            confidence = 0.6   # Средний уровень
            label = 'suspicious'
        elif risk_score >= 1:
            confidence = 0.3   # Низкий уровень - подозрительный
            label = 'suspicious'
        else:
            confidence = 0.1   # Нет риска
            label = 'normal'
        
        # Дополнительная градация для уверенности менее 50%
        if confidence < 0.5:
            if risk_score >= 3:
                label = 'suspicious'  # Подозрительный контент
            else:
                label = 'normal'      # Обычный контент
        
        # Извлекаем ключевые слова из результата анализа
        keywords = []
        if 'rule_based_result' in result:
            keywords = result['rule_based_result'].get('found_keywords', [])
        elif 'found_keywords' in result:
            keywords = result.get('found_keywords', [])
        
        # Если ключевые слова не найдены, пытаемся извлечь из факторов риска
        if not keywords:
            if 'rule_based_result' in result:
                risk_factors = result['rule_based_result'].get('risk_factors', [])
                keywords = [factor.split(':')[0] for factor in risk_factors if isinstance(factor, str) and ':' in factor]
            elif 'risk_factors' in result:
                risk_factors = result.get('risk_factors', [])
                keywords = [factor.split(':')[0] for factor in risk_factors if isinstance(factor, str) and ':' in factor]
        
        # Добавляем выделенный текст с маркерами
        highlighted_text = self._highlight_keywords(text, keywords)
        
        return {
            'label': label,
            'confidence': confidence,
            'keywords': keywords,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'highlighted_text': highlighted_text,
            'threat_color': self._get_threat_color(label, confidence)
        }
    
    def _highlight_keywords(self, text: str, keywords: List[str]) -> str:
        """Выделение ключевых слов в тексте с HTML-разметкой"""
        highlighted = text
        
        # Получаем все экстремистские ключевые слова для поиска
        all_keywords = []
        for category_words in self.extremist_keywords.values():
            all_keywords.extend(category_words)
        
        # Добавляем паттерны угроз и языка вражды
        all_keywords.extend(self.threat_patterns)
        all_keywords.extend(self.hate_speech_patterns)
        
        # Сортируем по длине (сначала длинные, чтобы избежать частичных замен)
        all_keywords.sort(key=len, reverse=True)
        
        for keyword in all_keywords:
            if keyword.lower() in text.lower():
                # Определяем цвет выделения в зависимости от типа ключевого слова
                if keyword in self.threat_patterns:
                    color_class = 'threat-keyword'  # Красный для угроз
                elif keyword in self.hate_speech_patterns:
                    color_class = 'hate-keyword'    # Оранжевый для языка вражды
                else:
                    color_class = 'extremist-keyword'  # Желтый для экстремистских слов
                
                # Заменяем с сохранением регистра
                import re
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                highlighted = pattern.sub(
                    f'<span class="{color_class}" title="Маркер: {keyword}">\\g<0></span>',
                    highlighted
                )
        
        return highlighted
    
    def _get_threat_color(self, label: str, confidence: float) -> str:
        """Определение цвета для уровня угрозы"""
        if label == 'extremist':
            if confidence >= 0.8:
                return '#dc3545'  # Красный - критическая угроза
            else:
                return '#fd7e14'  # Оранжевый - высокая угроза
        elif label == 'suspicious':
            return '#ffc107'      # Желтый - подозрительный контент
        else:
            return '#28a745'      # Зеленый - безопасный контент
    
    def save_model(self, filepath: str):
        """Сохранение обученной модели"""
        if self.best_model is None:
            raise Exception("No trained model to save")
        
        model_data = {
            'vectorizer': self.vectorizer,
            'model': self.best_model,
            'extremist_keywords': self.extremist_keywords,
            'hate_speech_patterns': self.hate_speech_patterns,
            'threat_patterns': self.threat_patterns
        }
        
        joblib.dump(model_data, filepath)
        self.logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Загрузка обученной модели"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        
        model_data = joblib.load(filepath)
        
        self.vectorizer = model_data['vectorizer']
        self.best_model = model_data['model']
        self.extremist_keywords = model_data['extremist_keywords']
        self.hate_speech_patterns = model_data['hate_speech_patterns']
        self.threat_patterns = model_data['threat_patterns']
        
        self.logger.info(f"Model loaded from {filepath}")
    
    def batch_analyze(self, texts: List[str]) -> List[Dict[str, any]]:
        """Пакетный анализ текстов"""
        results = []
        
        for text in texts:
            try:
                result = self.analyze_text_combined(text)
                result['text'] = text[:200] + '...' if len(text) > 200 else text
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error analyzing text: {e}")
                results.append({
                    'text': text[:200] + '...' if len(text) > 200 else text,
                    'error': str(e),
                    'risk_level': 'unknown',
                    'analysis_date': datetime.now()
                })
        
        return results