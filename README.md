echo "# breaking_news" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M master
git remote add origin https://github.com/nikola254/breaking_news.git
git push -u origin master


Запустить clickhouse в фоновом режиме
docker-compose up -d


http://localhost:18123/play
и тут выполняем запросы к БД

SHOW DATABASES;
SHOW TABLES FROM news;

SELECT title, source, parsed_date 
FROM news.ria_headlines  
ORDER BY parsed_date DESC 
LIMIT 10;


SELECT 
    title AS "Заголовок",
    content AS "Содержание статьи",
    parsed_date AS "Дата публикации",
    link AS "Ссылка"
FROM news.ria_headlines  
ORDER BY parsed_date DESC 
LIMIT 50;


SELECT 
    title AS "Заголовок",
    content AS "Содержание статьи",
    parsed_date AS "Дата публикации",
    link AS "Ссылка"
FROM news.israil_headlines  
ORDER BY parsed_date DESC;


SELECT
    title AS "Заголовок",
    content AS "Содержание новости",
    channel AS "Канал",
    parsed_date AS "Дата и время парсинга"
FROM news.telegram_headlines;