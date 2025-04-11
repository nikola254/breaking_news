from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def get_dynamic_page(url):
    # Настраиваем Chrome для работы в режиме headless
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    
    # Создаём экземпляр драйвера (убедитесь, что у вас установлен ChromeDriver и он доступен)
    driver = webdriver.Chrome(options=options)
    
    # Загружаем страницу
    driver.get(url)
    
    try:
        # Ожидаем появления элемента с классом "category-container" (например, до 10 секунд)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "category-container"))
        )
    except Exception as e:
        print("Элемент не найден или произошла ошибка ожидания:", e)
    
    # Получаем отрендеренный HTML-код страницы
    rendered_html = driver.page_source
    driver.quit()
    return rendered_html

if __name__ == "__main__":
    url = "https://www.7kanal.co.il/section/32"
    html = get_dynamic_page(url)
    soup = BeautifulSoup(html, "html.parser")
    
    # Ищем контейнер <div> с классом "category-container"
    container = soup.find("div", class_="category-container")
    if container:
        print("Контейнер найден!")
        # Здесь можно продолжить извлечение контента, например, искать внутри container тег <section> или конкретные ссылки
        # Например:
        section = container.find("section")
        if section:
            articles = section.find_all("a", class_="article article-sub-pages category-article")
            for article in articles:
                title_tag = article.find("h2", class_="article-content--title")
                title = title_tag.get_text(strip=True) if title_tag else article.get_text(strip=True)
                link = article.get("href")
                print("Заголовок:", title)
                print("Ссылка:", link)
                print("-" * 40)
    else:
        print("Контейнер с классом 'category-container' не найден")
