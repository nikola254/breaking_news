import requests
from bs4 import BeautifulSoup

def parse_politics_headlines():
    url = "https://ria.ru/world/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Проверка успешного запроса
    except requests.RequestException as e:
        print("Ошибка при получении данных:", e)
        return

    soup = BeautifulSoup(response.content, "html.parser")

    # Замените 'YOUR_DIV_CLASS_NAME' на актуальное название класса для контейнера статьи
    articles = soup.find_all("div", class_="list-item__content")
    
    if not articles:
        print("Не найдено ни одного контейнера с указанным классом")
        return

    for article in articles:
        # Ищем тег <a> с нужным классом внутри контейнера
        link_tag = article.find("a", class_="list-item__title color-font-hover-only")
        if link_tag:
            title = link_tag.get_text(strip=True)
            link = link_tag.get("href")
            print("Заголовок:", title)
            print("Ссылка:", link)
            print("-" * 40)
        else:
            print("В контейнере не найден тег <a> с классом 'list-item__title color-font-hover-only'.")

if __name__ == "__main__":
    parse_politics_headlines()
