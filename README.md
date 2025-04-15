echo "# breaking_news" >> README.md
git init
git add README.md
git commit -m "first commit"
git branch -M master
git remote add origin https://github.com/nikola254/breaking_news.git
git push -u origin master


Запустить clickhouse в фоновом режиме
docker-compose up -d


http://localhost:8123/play
и тут выполняем запросы к БД

SHOW DATABASES;
SHOW TABLES FROM news;

SELECT title, source, parsed_date 
FROM news.ria_headlines  
ORDER BY parsed_date DESC 
LIMIT 10;