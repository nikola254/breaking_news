"""
Тестовый датасет для анализа экстремистского контента в Telegram
Содержит примеры различных типов контента для тестирования и обучения модели
"""

from datetime import datetime, timedelta
import random

# Тестовые данные для различных типов контента
TEST_DATASET = {
    "normal": [
        {
            "id": "normal_1",
            "text": "Сегодня прекрасная погода! Планирую прогулку в парке с семьей. Надеюсь, все хорошо проведут выходные.",
            "author": "@family_channel",
            "date": datetime.now() - timedelta(hours=2),
            "views": 150,
            "forwards": 5,
            "replies": 12,
            "expected_classification": "normal",
            "expected_extremism_percentage": 0,
            "keywords": ["погода", "семья", "прогулка", "выходные"]
        },
        {
            "id": "normal_2", 
            "text": "Новый рецепт борща от бабушки! Ингредиенты: свекла, капуста, морковь, лук, мясо. Готовить 2 часа на медленном огне.",
            "author": "@cooking_tips",
            "date": datetime.now() - timedelta(hours=5),
            "views": 89,
            "forwards": 3,
            "replies": 8,
            "expected_classification": "normal",
            "expected_extremism_percentage": 0,
            "keywords": ["рецепт", "борщ", "готовка", "еда"]
        },
        {
            "id": "normal_3",
            "text": "Завтра начинается новый учебный семестр. Студенты готовятся к занятиям, покупают учебники и канцелярские принадлежности.",
            "author": "@university_news",
            "date": datetime.now() - timedelta(hours=8),
            "views": 234,
            "forwards": 12,
            "replies": 18,
            "expected_classification": "normal", 
            "expected_extremism_percentage": 5,
            "keywords": ["учеба", "семестр", "студенты", "университет"]
        },
        {
            "id": "normal_4",
            "text": "Концерт классической музыки в филармонии. Исполняется симфония Чайковского. Билеты можно купить в кассе.",
            "author": "@culture_events",
            "date": datetime.now() - timedelta(hours=12),
            "views": 67,
            "forwards": 2,
            "replies": 4,
            "expected_classification": "normal",
            "expected_extremism_percentage": 0,
            "keywords": ["концерт", "музыка", "Чайковский", "филармония"]
        },
        {
            "id": "normal_5",
            "text": "Спортивные новости: местная футбольная команда выиграла матч со счетом 3:1. Болельщики довольны результатом.",
            "author": "@sports_news",
            "date": datetime.now() - timedelta(hours=15),
            "views": 445,
            "forwards": 23,
            "replies": 31,
            "expected_classification": "normal",
            "expected_extremism_percentage": 0,
            "keywords": ["спорт", "футбол", "матч", "команда"]
        }
    ],
    
    "suspicious": [
        {
            "id": "suspicious_1",
            "text": "Власти снова принимают непопулярные решения. Народ должен знать правду о том, что происходит в стране. Время действовать!",
            "author": "@truth_seekers",
            "date": datetime.now() - timedelta(hours=3),
            "views": 1250,
            "forwards": 89,
            "replies": 156,
            "expected_classification": "suspicious",
            "expected_extremism_percentage": 25,
            "keywords": ["власти", "народ", "правда", "действовать"]
        },
        {
            "id": "suspicious_2",
            "text": "Официальные СМИ замалчивают важные события. Только мы говорим правду! Подписывайтесь и распространяйте информацию.",
            "author": "@alternative_media",
            "date": datetime.now() - timedelta(hours=6),
            "views": 890,
            "forwards": 67,
            "replies": 89,
            "expected_classification": "suspicious",
            "expected_extremism_percentage": 30,
            "keywords": ["СМИ", "замалчивают", "правда", "распространяйте"]
        },
        {
            "id": "suspicious_3",
            "text": "Система работает против простых людей. Пора объединяться и защищать свои права. Присоединяйтесь к нашему движению!",
            "author": "@peoples_movement",
            "date": datetime.now() - timedelta(hours=9),
            "views": 2100,
            "forwards": 145,
            "replies": 234,
            "expected_classification": "suspicious",
            "expected_extremism_percentage": 35,
            "keywords": ["система", "объединяться", "права", "движение"]
        },
        {
            "id": "suspicious_4",
            "text": "Коррупция достигла критического уровня. Чиновники воруют миллиарды, а народ нищает. Когда это закончится?",
            "author": "@anticorruption_watch",
            "date": datetime.now() - timedelta(hours=11),
            "views": 1567,
            "forwards": 123,
            "replies": 178,
            "expected_classification": "suspicious",
            "expected_extremism_percentage": 28,
            "keywords": ["коррупция", "чиновники", "воруют", "нищает"]
        },
        {
            "id": "suspicious_5",
            "text": "Готовится новый закон, который ограничит наши свободы. Мы не можем этого допустить! Выходите на митинги!",
            "author": "@freedom_fighters",
            "date": datetime.now() - timedelta(hours=14),
            "views": 3400,
            "forwards": 267,
            "replies": 445,
            "expected_classification": "suspicious",
            "expected_extremism_percentage": 40,
            "keywords": ["закон", "ограничит", "свободы", "митинги"]
        }
    ],
    
    "extremist": [
        {
            "id": "extremist_1",
            "text": "Враги народа должны быть наказаны! Пора взять правосудие в свои руки. Они не заслуживают пощады!",
            "author": "@radical_justice",
            "date": datetime.now() - timedelta(hours=1),
            "views": 2890,
            "forwards": 234,
            "replies": 567,
            "expected_classification": "extremist",
            "expected_extremism_percentage": 85,
            "keywords": ["враги", "наказаны", "правосудие", "пощады"]
        },
        {
            "id": "extremist_2",
            "text": "Уничтожить всех предателей! Только радикальные меры спасут нашу родину. Смерть изменникам!",
            "author": "@patriots_revenge",
            "date": datetime.now() - timedelta(hours=4),
            "views": 4567,
            "forwards": 456,
            "replies": 789,
            "expected_classification": "extremist",
            "expected_extremism_percentage": 95,
            "keywords": ["уничтожить", "предателей", "смерть", "изменникам"]
        },
        {
            "id": "extremist_3",
            "text": "Террористы захватили власть! Народ, вооружайтесь! Только силой можно восстановить справедливость!",
            "author": "@armed_resistance",
            "date": datetime.now() - timedelta(hours=7),
            "views": 5234,
            "forwards": 567,
            "replies": 890,
            "expected_classification": "extremist",
            "expected_extremism_percentage": 90,
            "keywords": ["террористы", "вооружайтесь", "силой", "справедливость"]
        },
        {
            "id": "extremist_4",
            "text": "Взрывы и теракты - единственный способ достучаться до власти. Готовьте бомбы, товарищи!",
            "author": "@bomb_makers",
            "date": datetime.now() - timedelta(hours=10),
            "views": 3456,
            "forwards": 345,
            "replies": 678,
            "expected_classification": "extremist",
            "expected_extremism_percentage": 98,
            "keywords": ["взрывы", "теракты", "бомбы", "товарищи"]
        },
        {
            "id": "extremist_5",
            "text": "Убить всех неверных! Джихад - священная война! Аллах велик! Смерть неверующим!",
            "author": "@holy_warriors",
            "date": datetime.now() - timedelta(hours=13),
            "views": 2789,
            "forwards": 278,
            "replies": 456,
            "expected_classification": "extremist",
            "expected_extremism_percentage": 99,
            "keywords": ["убить", "неверных", "джихад", "смерть"]
        }
    ]
}

# Функция для получения случайного сообщения определенного типа
def get_random_message(content_type="normal"):
    """Получить случайное сообщение определенного типа"""
    if content_type not in TEST_DATASET:
        content_type = "normal"
    
    messages = TEST_DATASET[content_type]
    return random.choice(messages)

# Функция для получения всех сообщений определенного типа
def get_messages_by_type(content_type="normal"):
    """Получить все сообщения определенного типа"""
    return TEST_DATASET.get(content_type, [])

# Функция для получения смешанного датасета
def get_mixed_dataset(normal_count=5, suspicious_count=3, extremist_count=2):
    """Получить смешанный датасет с заданным количеством сообщений каждого типа"""
    dataset = []
    
    # Добавляем нормальные сообщения
    normal_messages = TEST_DATASET["normal"][:normal_count]
    dataset.extend(normal_messages)
    
    # Добавляем подозрительные сообщения
    suspicious_messages = TEST_DATASET["suspicious"][:suspicious_count]
    dataset.extend(suspicious_messages)
    
    # Добавляем экстремистские сообщения
    extremist_messages = TEST_DATASET["extremist"][:extremist_count]
    dataset.extend(extremist_messages)
    
    # Перемешиваем датасет
    random.shuffle(dataset)
    
    return dataset

# Функция для получения статистики датасета
def get_dataset_stats():
    """Получить статистику тестового датасета"""
    stats = {}
    total_messages = 0
    
    for content_type, messages in TEST_DATASET.items():
        count = len(messages)
        stats[content_type] = count
        total_messages += count
    
    stats["total"] = total_messages
    return stats

# Функция для валидации классификации
def validate_classification(message_id, predicted_classification, predicted_percentage):
    """Проверить правильность классификации сообщения"""
    for content_type, messages in TEST_DATASET.items():
        for message in messages:
            if message["id"] == message_id:
                expected_class = message["expected_classification"]
                expected_percentage = message["expected_extremism_percentage"]
                
                # Проверяем классификацию
                class_correct = predicted_classification == expected_class
                
                # Проверяем процент (допускаем отклонение в 15%)
                percentage_diff = abs(predicted_percentage - expected_percentage)
                percentage_correct = percentage_diff <= 15
                
                return {
                    "message_id": message_id,
                    "expected_classification": expected_class,
                    "predicted_classification": predicted_classification,
                    "expected_percentage": expected_percentage,
                    "predicted_percentage": predicted_percentage,
                    "classification_correct": class_correct,
                    "percentage_correct": percentage_correct,
                    "overall_correct": class_correct and percentage_correct
                }
    
    return None

# Функция для тестирования модели на всем датасете
def test_model_accuracy(classifier_function):
    """Тестировать точность модели на всем датасете"""
    results = []
    correct_classifications = 0
    correct_percentages = 0
    total_messages = 0
    
    for content_type, messages in TEST_DATASET.items():
        for message in messages:
            # Получаем предсказание модели
            prediction = classifier_function(message["text"])
            
            # Валидируем результат
            validation = validate_classification(
                message["id"],
                prediction.get("classification", "normal"),
                prediction.get("extremism_percentage", 0)
            )
            
            if validation:
                results.append(validation)
                total_messages += 1
                
                if validation["classification_correct"]:
                    correct_classifications += 1
                
                if validation["percentage_correct"]:
                    correct_percentages += 1
    
    # Вычисляем точность
    classification_accuracy = (correct_classifications / total_messages) * 100 if total_messages > 0 else 0
    percentage_accuracy = (correct_percentages / total_messages) * 100 if total_messages > 0 else 0
    overall_accuracy = ((correct_classifications + correct_percentages) / (total_messages * 2)) * 100 if total_messages > 0 else 0
    
    return {
        "total_messages": total_messages,
        "correct_classifications": correct_classifications,
        "correct_percentages": correct_percentages,
        "classification_accuracy": round(classification_accuracy, 2),
        "percentage_accuracy": round(percentage_accuracy, 2),
        "overall_accuracy": round(overall_accuracy, 2),
        "detailed_results": results
    }

if __name__ == "__main__":
    # Пример использования
    print("Статистика тестового датасета:")
    stats = get_dataset_stats()
    for content_type, count in stats.items():
        print(f"{content_type}: {count} сообщений")
    
    print("\nПример смешанного датасета:")
    mixed = get_mixed_dataset(2, 2, 1)
    for msg in mixed:
        print(f"[{msg['expected_classification']}] {msg['text'][:50]}...")