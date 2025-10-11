"""
Модуль для предобработки новостного текста
Удаляет ссылки, эмодзи, смайлики и другой мусор
"""
import re
import emoji

class NewsPreprocessor:
    """Класс для очистки и предобработки новостного текста"""
    
    def __init__(self):
        # Паттерны для удаления
        self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
        self.telegram_link_pattern = re.compile(r't\.me/[a-zA-Z0-9_]+')
        self.html_tags_pattern = re.compile(r'<[^>]+>')
        self.mention_pattern = re.compile(r'@[a-zA-Z0-9_]+')
        self.hashtag_pattern = re.compile(r'#[а-яА-ЯёЁa-zA-Z0-9_]+')
        
        # Паттерны для медиа-файлов
        self.image_pattern = re.compile(r'\[фото\]|\[картинка\]|\[изображение\]|\[photo\]|\[image\]|\[img\]', re.IGNORECASE)
        self.video_pattern = re.compile(r'\[видео\]|\[video\]|\[ролик\]', re.IGNORECASE)
        self.audio_pattern = re.compile(r'\[аудио\]|\[audio\]|\[голосовое\]', re.IGNORECASE)
        
        # Множественные пробелы и переносы
        self.whitespace_pattern = re.compile(r'\s+')
        
    def remove_urls(self, text):
        """Удаляет все URL из текста"""
        text = self.url_pattern.sub('', text)
        text = self.telegram_link_pattern.sub('', text)
        return text
    
    def remove_emails(self, text):
        """Удаляет email адреса"""
        return self.email_pattern.sub('', text)
    
    def remove_html_tags(self, text):
        """Удаляет HTML теги"""
        return self.html_tags_pattern.sub('', text)
    
    def remove_mentions(self, text):
        """Удаляет упоминания (@username)"""
        return self.mention_pattern.sub('', text)
    
    def remove_hashtags(self, text):
        """Удаляет хэштеги"""
        return self.hashtag_pattern.sub('', text)
    
    def remove_emojis(self, text):
        """Удаляет эмодзи и смайлики"""
        # Удаляем Unicode эмодзи
        text = emoji.replace_emoji(text, replace='')
        
        # Удаляем текстовые смайлики
        emoticons_pattern = re.compile(r'[:;=]-?[)D(]|\^_\^|>_<|T_T|\(╯°□°\)╯︵ ┻━┻')
        text = emoticons_pattern.sub('', text)
        
        return text
    
    def remove_media_references(self, text):
        """Удаляет ссылки на медиа-файлы"""
        text = self.image_pattern.sub('', text)
        text = self.video_pattern.sub('', text)
        text = self.audio_pattern.sub('', text)
        return text
    
    def fix_missing_spaces(self, text):
        """
        Исправляет отсутствующие пробелы между словами
        Примеры проблем: "палестинскоедвижение", "освобожденияПалестины"
        """
        if not text:
            return ""
        
        # Паттерн: строчная буква + заглавная буква (кириллица)
        text = re.sub(r'([а-я])([А-Я])', r'\1 \2', text)
        
        # Паттерн: строчная буква + заглавная буква (латиница)
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        return text
    
    def normalize_whitespace(self, text):
        """Нормализует пробелы и переносы строк"""
        # Заменяем множественные пробелы на один
        text = self.whitespace_pattern.sub(' ', text)
        # Убираем пробелы в начале и конце
        text = text.strip()
        return text
    
    def clean_text(self, text, 
                   remove_urls=True,
                   remove_emails=True,
                   remove_html=True,
                   remove_mentions=False,  # Оставляем упоминания по умолчанию
                   remove_hashtags=False,  # Оставляем хэштеги по умолчанию
                   remove_emojis=True,
                   remove_media=True,
                   fix_spaces=True):
        """
        Полная очистка текста
        
        Args:
            text: Исходный текст
            remove_urls: Удалять ли URL
            remove_emails: Удалять ли email
            remove_html: Удалять ли HTML теги
            remove_mentions: Удалять ли упоминания
            remove_hashtags: Удалять ли хэштеги
            remove_emojis: Удалять ли эмодзи
            remove_media: Удалять ли ссылки на медиа
            fix_spaces: Исправлять ли склеенные слова
            
        Returns:
            Очищенный текст
        """
        if not text:
            return ""
        
        # Применяем все фильтры
        if remove_html:
            text = self.remove_html_tags(text)
        
        # Исправляем склеенные слова после удаления HTML тегов
        if fix_spaces:
            text = self.fix_missing_spaces(text)
        
        if remove_urls:
            text = self.remove_urls(text)
        
        if remove_emails:
            text = self.remove_emails(text)
        
        if remove_mentions:
            text = self.remove_mentions(text)
        
        if remove_hashtags:
            text = self.remove_hashtags(text)
        
        if remove_emojis:
            text = self.remove_emojis(text)
        
        if remove_media:
            text = self.remove_media_references(text)
        
        # Нормализуем пробелы в конце
        text = self.normalize_whitespace(text)
        
        return text
    
    def preprocess_article(self, title, content):
        """
        Предобработка статьи (заголовок + контент)
        
        Args:
            title: Заголовок статьи
            content: Содержание статьи
            
        Returns:
            tuple: (cleaned_title, cleaned_content)
        """
        cleaned_title = self.clean_text(title, 
                                         remove_mentions=False,
                                         remove_hashtags=False,
                                         fix_spaces=True)
        
        cleaned_content = self.clean_text(content,
                                          remove_mentions=False,
                                          remove_hashtags=False,
                                          fix_spaces=True)
        
        return cleaned_title, cleaned_content


# Создаем глобальный экземпляр для использования в парсерах
preprocessor = NewsPreprocessor()


if __name__ == '__main__':
    # Тестирование
    test_text = """
    Привет! 😀 Посмотрите это видео https://example.com/video.mp4
    Подписывайтесь на @username и используйте #хэштег
    [фото] [видео]
    Email: test@example.com
    <b>HTML теги</b>
    🎉🎊 Множество   пробелов    здесь
    палестинскоедвижение освобожденияПалестины
    """
    
    preprocessor = NewsPreprocessor()
    cleaned = preprocessor.clean_text(test_text)
    print("Исходный текст:")
    print(test_text)
    print("\nОчищенный текст:")
    print(cleaned)
    
    # Тестирование исправления пробелов
    test_spaces = "палестинскоедвижение освобожденияПалестины"
    fixed = preprocessor.fix_missing_spaces(test_spaces)
    print(f"\nТест исправления пробелов:")
    print(f"До: {test_spaces}")
    print(f"После: {fixed}")


