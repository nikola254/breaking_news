# Используем базовый образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем файлы приложения
COPY . .

# Открываем порт 5000 для Flask
EXPOSE 5000

# Запускаем приложение
CMD ["python", "run.py"]