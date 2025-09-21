# Тестирование эндпоинтов приложения Breaking News
Write-Host "🚀 Тестирование эндпоинтов Breaking News" -ForegroundColor Green
Write-Host "=" * 50

$baseUrl = "http://127.0.0.1:5000"
$successCount = 0
$totalCount = 0

# Функция для тестирования эндпоинта
function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$ExpectedContentType = "text/html"
    )
    
    $global:totalCount++
    Write-Host "🔍 Тестирую: $Name" -ForegroundColor Cyan
    Write-Host "URL: $Url"
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 10
        $statusCode = $response.StatusCode
        $contentType = $response.Headers["Content-Type"]
        
        Write-Host "Статус: $statusCode" -ForegroundColor Green
        Write-Host "Content-Type: $contentType"
        
        if ($statusCode -eq 200) {
            Write-Host "✅ Успешно" -ForegroundColor Green
            $global:successCount++
            
            # Дополнительная проверка для API эндпоинтов
            if ($Url -like "*/api/*" -and $contentType -like "*json*") {
                try {
                    $jsonData = $response.Content | ConvertFrom-Json
                    Write-Host "📊 JSON данные получены корректно"
                } catch {
                    Write-Host "⚠️ Ошибка парсинга JSON: $($_.Exception.Message)" -ForegroundColor Yellow
                }
            }
        } else {
            Write-Host "❌ Неожиданный статус: $statusCode" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    }
    
    Write-Host ""
}

# Тестирование страниц
Write-Host "📄 Тестирование страниц:" -ForegroundColor Yellow
Write-Host ""

Test-Endpoint "Главная страница" "$baseUrl/"
Test-Endpoint "Аналитика" "$baseUrl/analytics"
Test-Endpoint "База данных" "$baseUrl/clickhouse"
Test-Endpoint "Прогнозы" "$baseUrl/predict"
Test-Endpoint "О проекте" "$baseUrl/about"

# Тестирование API
Write-Host "🔌 Тестирование API:" -ForegroundColor Yellow
Write-Host ""

Test-Endpoint "API новостей" "$baseUrl/api/news" "application/json"
Test-Endpoint "Статистика новостей" "$baseUrl/api/news/statistics" "application/json"
Test-Endpoint "Распределение по источникам" "$baseUrl/api/charts/source-distribution" "application/json"
Test-Endpoint "Анализ настроений" "$baseUrl/api/charts/sentiment-analysis" "application/json"
Test-Endpoint "Временная линия" "$baseUrl/api/charts/timeline" "application/json"
Test-Endpoint "Категории новостей" "$baseUrl/api/charts/category-distribution" "application/json"

# Тестирование специфичных эндпоинтов для Украины
Write-Host "🇺🇦 Тестирование эндпоинтов Украины:" -ForegroundColor Yellow
Write-Host ""

Test-Endpoint "Временная линия Украины" "$baseUrl/api/ukraine/timeline" "application/json"
Test-Endpoint "Анализ настроений Украины" "$baseUrl/api/ukraine/sentiment" "application/json"
Test-Endpoint "Источники новостей Украины" "$baseUrl/api/ukraine/sources" "application/json"

# Результаты
Write-Host "=" * 50
Write-Host "📊 Результаты: $successCount/$totalCount успешных тестов" -ForegroundColor $(if ($successCount -eq $totalCount) { "Green" } else { "Yellow" })

if ($successCount -eq $totalCount) {
    Write-Host "🎉 Все тесты прошли успешно!" -ForegroundColor Green
} elseif ($successCount -gt 0) {
    Write-Host "⚠️ Частично работает" -ForegroundColor Yellow
} else {
    Write-Host "🚨 Ничего не работает" -ForegroundColor Red
}