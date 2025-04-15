from clickhouse_driver import Client

def get_headlines_from_clickhouse(limit=10):
    """
    Подключается к ClickHouse и выбирает последние заголовки из таблицы news.ria_headlines.
    """
    client = Client(host='localhost', port=9000)
    
    query = f"""
        SELECT title 
        FROM news.ria_headlines
        ORDER BY parsed_date DESC
        LIMIT {limit}
    """
    # Выполняем запрос и извлекаем заголовки (каждый результат – кортеж, поэтому берем 0-ой элемент)
    result = client.execute(query)
    headlines = [row[0] for row in result]
    return headlines

def generate_prompt(headlines, policy="the current political situation"):
    """
    Формирует текстовый промт для нейросети, используя переданные заголовки и указанный контекст политики.
    
    :param headlines: список заголовков
    :param policy: тема или политика, развитие которой нужно прогнозировать
    :return: строка с сформированным промтом
    """
    # Приводим заголовки к текстовому виду
    headlines_text = "\n".join([f"- {h}" for h in headlines])
    
    prompt = f"""Based on the following recent news headlines:

{headlines_text}

Analyze the current situation and provide a forecast on how {policy} will develop in the near future. Your analysis should highlight key factors and potential outcomes.
"""
    return prompt.strip()

if __name__ == "__main__":
    # Получаем заголовки (например, последние 10 новостей)
    headlines = get_headlines_from_clickhouse(limit=10)
    
    # Замените "politics in [Country/World]" на желаемый контекст, например, "politics in Ukraine" или "global political trends"
    prompt = generate_prompt(headlines, policy="global political trends")
    
    print("Generated prompt for the neural network:\n")
    print(prompt)
