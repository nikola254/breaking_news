"""
Расширенный тестовый датасет для обучения модели анализа экстремистского контента
Содержит примеры нормального, подозрительного и экстремистского контента
"""

from datetime import datetime, timedelta
import random

# Расширенный датасет для обучения модели
EXTREMISM_TRAINING_DATASET = {
    "normal": [
        {
            "id": "normal_1",
            "text": "Сегодня прекрасная погода! Планирую прогулку в парке с семьей. Надеюсь, все хорошо проведут выходные.",
            "classification": "normal",
            "extremism_score": 0.0,
            "keywords": ["погода", "семья", "прогулка", "выходные"],
            "extremist_phrases": []
        },
        {
            "id": "normal_2",
            "text": "Новый рецепт борща от бабушки! Ингредиенты: свекла, капуста, морковь, лук, мясо. Готовить 2 часа на медленном огне.",
            "classification": "normal",
            "extremism_score": 0.0,
            "keywords": ["рецепт", "борщ", "готовить"],
            "extremist_phrases": []
        },
        {
            "id": "normal_3",
            "text": "Завтра начинается новый учебный год. Желаю всем студентам успехов в учебе и интересных открытий!",
            "classification": "normal",
            "extremism_score": 0.0,
            "keywords": ["учеба", "студенты", "успех"],
            "extremist_phrases": []
        },
        {
            "id": "normal_4",
            "text": "Отличный концерт вчера! Музыканты играли с душой, публика была в восторге. Спасибо организаторам за прекрасный вечер.",
            "classification": "normal",
            "extremism_score": 0.0,
            "keywords": ["концерт", "музыка", "организаторы"],
            "extremist_phrases": []
        },
        {
            "id": "normal_5",
            "text": "Важно помнить о правилах дорожного движения. Безопасность на дорогах - это ответственность каждого водителя.",
            "classification": "normal",
            "extremism_score": 0.0,
            "keywords": ["безопасность", "дороги", "ответственность"],
            "extremist_phrases": []
        }
    ],
    
    "suspicious": [
        {
            "id": "suspicious_1",
            "text": "Эти политики совсем обнаглели! Пора показать им, кто здесь хозяин. Народ должен восстать против этой несправедливости!",
            "classification": "suspicious",
            "extremism_score": 0.4,
            "keywords": ["политики", "восстать", "несправедливость"],
            "extremist_phrases": ["пора показать", "народ должен восстать"]
        },
        {
            "id": "suspicious_2",
            "text": "Мигранты захватывают наши рабочие места. Нужно что-то делать с этой проблемой, иначе наша страна погибнет.",
            "classification": "suspicious",
            "extremism_score": 0.5,
            "keywords": ["мигранты", "захватывают", "проблема"],
            "extremist_phrases": ["захватывают", "страна погибнет"]
        },
        {
            "id": "suspicious_3",
            "text": "Власть нас обманывает! Они воруют наши деньги, а мы молчим. Хватит терпеть это безобразие!",
            "classification": "suspicious",
            "extremism_score": 0.3,
            "keywords": ["власть", "обманывает", "воруют"],
            "extremist_phrases": ["хватит терпеть"]
        },
        {
            "id": "suspicious_4",
            "text": "СМИ промывают нам мозги ложной информацией. Пора открыть глаза и увидеть правду о том, что происходит!",
            "classification": "suspicious",
            "extremism_score": 0.4,
            "keywords": ["СМИ", "промывают мозги", "ложная информация"],
            "extremist_phrases": ["промывают мозги", "пора открыть глаза"]
        },
        {
            "id": "suspicious_5",
            "text": "Система образования разрушает традиционные ценности. Наших детей учат неправильным вещам!",
            "classification": "suspicious",
            "extremism_score": 0.3,
            "keywords": ["система образования", "традиционные ценности", "дети"],
            "extremist_phrases": ["разрушает", "неправильным вещам"]
        }
    ],
    
    "extremist": [
        {
            "id": "extremist_1",
            "text": "Смерть врагам народа! Пора взять оружие и уничтожить всех предателей. Только насилие может спасти нашу родину!",
            "classification": "extremist",
            "extremism_score": 0.9,
            "keywords": ["смерть", "оружие", "уничтожить", "насилие"],
            "extremist_phrases": ["смерть врагам", "взять оружие", "уничтожить всех", "только насилие"]
        },
        {
            "id": "extremist_2",
            "text": "Убить всех неверных! Джихад - священная война против кафиров. Аллах велик, смерть неверующим!",
            "classification": "extremist",
            "extremism_score": 0.95,
            "keywords": ["убить", "джихад", "война", "смерть"],
            "extremist_phrases": ["убить всех", "священная война", "смерть неверующим"]
        },
        {
            "id": "extremist_3",
            "text": "Взорвем эти правительственные здания! Террор - единственный способ достучаться до власти. Готовьте бомбы!",
            "classification": "extremist",
            "extremism_score": 0.98,
            "keywords": ["взорвем", "террор", "бомбы", "власть"],
            "extremist_phrases": ["взорвем", "террор - единственный способ", "готовьте бомбы"]
        },
        {
            "id": "extremist_4",
            "text": "Расовая чистота превыше всего! Уничтожим всех представителей низших рас. Белая раса должна господствовать!",
            "classification": "extremist",
            "extremism_score": 0.92,
            "keywords": ["расовая чистота", "уничтожим", "низшие расы"],
            "extremist_phrases": ["расовая чистота", "уничтожим всех", "должна господствовать"]
        },
        {
            "id": "extremist_5",
            "text": "Призываю к священной войне против неверных! Каждый истинный верующий должен взять в руки оружие и сражаться!",
            "classification": "extremist",
            "extremism_score": 0.88,
            "keywords": ["священная война", "неверные", "оружие", "сражаться"],
            "extremist_phrases": ["священная война", "взять в руки оружие", "должен сражаться"]
        }
    ]
}

# Функция для получения всех примеров с метками
def get_training_data():
    """Возвращает все примеры с метками для обучения модели"""
    texts = []
    labels = []
    
    # Нормальный контент (метка 0)
    for item in EXTREMISM_TRAINING_DATASET["normal"]:
        texts.append(item["text"])
        labels.append(0)
    
    # Подозрительный контент (метка 1)
    for item in EXTREMISM_TRAINING_DATASET["suspicious"]:
        texts.append(item["text"])
        labels.append(1)
    
    # Экстремистский контент (метка 2)
    for item in EXTREMISM_TRAINING_DATASET["extremist"]:
        texts.append(item["text"])
        labels.append(2)
    
    return texts, labels

# Функция для получения примеров по типу
def get_examples_by_type(content_type):
    """Возвращает примеры определенного типа"""
    if content_type in EXTREMISM_TRAINING_DATASET:
        return EXTREMISM_TRAINING_DATASET[content_type]
    return []

# Функция для добавления нового примера
def add_training_example(text, classification, extremism_score, keywords, extremist_phrases):
    """Добавляет новый пример в датасет"""
    new_id = f"{classification}_{len(EXTREMISM_TRAINING_DATASET[classification]) + 1}"
    
    new_example = {
        "id": new_id,
        "text": text,
        "classification": classification,
        "extremism_score": extremism_score,
        "keywords": keywords,
        "extremist_phrases": extremist_phrases
    }
    
    EXTREMISM_TRAINING_DATASET[classification].append(new_example)
    return new_example

# Статистика датасета
def get_dataset_stats():
    """Возвращает статистику датасета"""
    stats = {}
    total_examples = 0
    
    for content_type, examples in EXTREMISM_TRAINING_DATASET.items():
        count = len(examples)
        stats[content_type] = count
        total_examples += count
    
    stats["total"] = total_examples
    return stats

if __name__ == "__main__":
    # Вывод статистики датасета
    stats = get_dataset_stats()
    print("Статистика тестового датасета:")
    print(f"Нормальный контент: {stats['normal']} примеров")
    print(f"Подозрительный контент: {stats['suspicious']} примеров")
    print(f"Экстремистский контент: {stats['extremist']} примеров")
    print(f"Всего примеров: {stats['total']}")
    
    # Пример использования
    texts, labels = get_training_data()
    print(f"\nПодготовлено {len(texts)} текстов для обучения модели")