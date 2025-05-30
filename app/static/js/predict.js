// Начальное значение остатка токенов (можно будет получать с сервера)
const INITIAL_TOKEN_BALANCE = 998300;
let currentTokenBalance = INITIAL_TOKEN_BALANCE;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Инициализация ползунка токенов
    const tokensSlider = document.getElementById('max_tokens');
    const tokensValue = document.getElementById('tokens-value');
    
    // Обновление отображаемого значения при перемещении ползунка
    tokensSlider.addEventListener('input', function() {
        tokensValue.textContent = this.value;
    });
    
    // Обновление баланса токенов при загрузке страницы
    updateTokenBalance(currentTokenBalance);
});

// Функция для обновления отображения баланса токенов
function updateTokenBalance(balance) {
    const balanceElement = document.getElementById('tokens-balance');
    if (balanceElement) {
        balanceElement.textContent = balance.toLocaleString();
        
        // Изменение цвета в зависимости от остатка
        if (balance < 1000) {
            balanceElement.style.color = '#ff7043'; // Оранжевый/красный для низкого баланса
        } else if (balance < 3000) {
            balanceElement.style.color = '#ffc107'; // Желтый для среднего баланса
        } else {
            balanceElement.style.color = '#4caf50'; // Зеленый для хорошего баланса
        }
    }
}

function sendToAI() {
    const prompt = document.getElementById('ai-prompt').value;
    const responseBox = document.getElementById('ai-response');
    const temperature = parseFloat(document.getElementById('temperature').value) || 0.7;
    const maxTokens = parseInt(document.getElementById('max_tokens').value) || 2048;
    const model = document.getElementById('ai-model').value;
    
    if (!prompt.trim()) {
        responseBox.innerHTML = '<span style="color: #ff7043;">Пожалуйста, введите запрос</span>';
        return;
    }
    
    // Показываем индикатор загрузки и текст "думаю..."
    responseBox.innerHTML = '<span class="thinking-text">Думаю...</span>';
    responseBox.classList.add('loading');
    
    // Используем только AI.IO API с моделью DeepSeek-R1
    const apiEndpoint = '/api/aiio/chat';
    const requestBody = {
        prompt: prompt,
        system_prompt: 'You are a helpful assistant.',
        temperature: temperature,
        max_tokens: maxTokens
    };
    
    fetch(apiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    })
    .then(res => res.json())
    .then(data => {
        responseBox.classList.remove('loading');
        if (data.status === 'success') {
            // Форматирование ответа с поддержкой переносов строк и сохранением форматирования
            const formattedResponse = data.response
                .replace(/\n/g, '<br>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>');
            
            responseBox.innerHTML = formattedResponse;
            
            // Отображение информации об использовании токенов, если доступно
            if (data.usage) {
                const usedTokens = data.usage.total_tokens || 0;
                
                // Обновляем баланс токенов (вычитаем использованные)
                currentTokenBalance -= usedTokens;
                if (currentTokenBalance < 0) currentTokenBalance = 0;
                updateTokenBalance(currentTokenBalance);
                
                const usageInfo = document.createElement('div');
                usageInfo.className = 'usage-info';
                usageInfo.textContent = `Использовано токенов: ${usedTokens}`;
                responseBox.appendChild(usageInfo);
            }
        } else {
            responseBox.innerHTML = `<span style="color: #ff7043;">Ошибка: ${data.message}</span>`;
        }
    })
    .catch(err => {
        responseBox.classList.remove('loading');
        responseBox.innerHTML = `<span style="color: #ff7043;">Сетевая ошибка: ${err.message}</span>`;
    });
}

// Функция для генерации прогноза социальной напряженности
function generateForecast() {
    const prompt = document.getElementById('ai-prompt').value;
    const responseBox = document.getElementById('ai-response');
    const chartContainer = document.getElementById('forecast-chart');
    const temperature = parseFloat(document.getElementById('temperature').value) || 0.7;
    const maxTokens = parseInt(document.getElementById('max_tokens').value) || 2048;
    
    // Получаем выбранные пользователем параметры
    const newsCategory = document.getElementById('news-category').value;
    const analysisPeriod = parseInt(document.getElementById('analysis-period').value);
    const forecastPeriod = parseInt(document.getElementById('forecast-period').value);
    
    // Показываем индикатор загрузки и текст "генерирую прогноз..."
    responseBox.innerHTML = '<span class="thinking-text">Генерирую прогноз...</span>';
    responseBox.classList.add('loading');
    chartContainer.innerHTML = '';
    
    // Формируем системный промт для DeepSeek с инструкциями по анализу данных
    const systemPrompt = `Ты - аналитик социальной напряженности. Проанализируй новостные данные из категории "${getReadableCategoryName(newsCategory)}" за последние ${getReadableTimePeriod(analysisPeriod)} и сделай прогноз социальной напряженности на ${getReadableTimePeriod(forecastPeriod)} вперед. Используй данные из ClickHouse для анализа. Твой ответ должен включать: 1) Общую оценку текущей ситуации, 2) Прогноз изменения индекса напряженности, 3) Ключевые факторы влияния, 4) Рекомендации.`;
    
    // Сначала отправляем запрос на генерацию прогноза через API
    const forecastApiEndpoint = '/api/generate_forecast';
    const forecastRequestBody = {
        category: newsCategory,
        analysis_period: analysisPeriod,
        forecast_period: forecastPeriod
    };
    
    fetch(forecastApiEndpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(forecastRequestBody)
    })
    .then(res => res.json())
    .then(forecastData => {
        if (forecastData.status === 'success') {
            // Отображаем графики прогноза
            if (forecastData.tension_forecast && forecastData.tension_forecast.chart_url) {
                const tensionChart = document.createElement('img');
                tensionChart.src = forecastData.tension_forecast.chart_url;
                tensionChart.alt = 'График прогноза напряженности';
                tensionChart.className = 'forecast-chart-img';
                chartContainer.appendChild(tensionChart);
            }
            
            if (forecastData.topics_forecast && forecastData.topics_forecast.chart_url) {
                const topicsChart = document.createElement('img');
                topicsChart.src = forecastData.topics_forecast.chart_url;
                topicsChart.alt = 'График распределения тем';
                topicsChart.className = 'forecast-chart-img';
                chartContainer.appendChild(topicsChart);
            }
            
            // Теперь отправляем запрос к DeepSeek для получения текстового анализа
            // Только если пользователь ввел дополнительный запрос или у нас есть данные прогноза
            if (prompt.trim() || (forecastData.tension_forecast && forecastData.tension_forecast.values)) {
                // Формируем контекст для DeepSeek на основе данных прогноза
                let contextData = '';
                
                if (forecastData.tension_forecast && forecastData.tension_forecast.values) {
                    contextData += '\nДанные прогноза напряженности:\n';
                    forecastData.tension_forecast.values.forEach(item => {
                        contextData += `${item.date}: ${(item.value * 100).toFixed(1)}% (диапазон: ${(item.lower_bound * 100).toFixed(1)}%-${(item.upper_bound * 100).toFixed(1)}%)\n`;
                    });
                }
                
                if (forecastData.topics_forecast && forecastData.topics_forecast.topics) {
                    contextData += '\nРаспределение тем:\n';
                    forecastData.topics_forecast.topics.forEach(topic => {
                        const changeSymbol = topic.change > 0 ? '↑' : (topic.change < 0 ? '↓' : '→');
                        contextData += `${topic.name}: ${(topic.value * 100).toFixed(1)}% (${changeSymbol}${Math.abs(topic.change * 100).toFixed(1)}%)\n`;
                    });
                }
                
                // Формируем запрос для DeepSeek
                const userPrompt = prompt.trim() ? prompt : 'Проанализируй данные прогноза и дай оценку ситуации';
                const aiPrompt = userPrompt + '\n\nКонтекст:\n' + contextData;
                
                // Отправляем запрос к DeepSeek
                const aiioEndpoint = '/api/aiio/chat';
                const aiioRequestBody = {
                    prompt: aiPrompt,
                    system_prompt: systemPrompt,
                    temperature: temperature,
                    max_tokens: maxTokens
                };
                
                return fetch(aiioEndpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(aiioRequestBody)
                }).then(res => res.json());
            } else {
                // Если нет дополнительного запроса и нет данных прогноза, просто показываем графики
                responseBox.classList.remove('loading');
                responseBox.innerHTML = '<p>Прогноз сгенерирован. Смотрите графики ниже.</p>';
                return null;
            }
        } else {
            throw new Error(forecastData.message || 'Ошибка при генерации прогноза');
        }
    })
    .then(aiioData => {
        if (aiioData) {
            responseBox.classList.remove('loading');
            if (aiioData.status === 'success') {
                // Форматирование ответа с поддержкой переносов строк и сохранением форматирования
                const formattedResponse = aiioData.response
                    .replace(/\n/g, '<br>')
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>');
                
                responseBox.innerHTML = formattedResponse;
                
                // Отображение информации об использовании токенов, если доступно
                if (aiioData.usage) {
                    const usedTokens = aiioData.usage.total_tokens || 0;
                    
                    // Обновляем баланс токенов (вычитаем использованные)
                    currentTokenBalance -= usedTokens;
                    if (currentTokenBalance < 0) currentTokenBalance = 0;
                    updateTokenBalance(currentTokenBalance);
                    
                    const usageInfo = document.createElement('div');
                    usageInfo.className = 'usage-info';
                    usageInfo.textContent = `Использовано токенов: ${usedTokens}`;
                    responseBox.appendChild(usageInfo);
                }
            } else {
                responseBox.innerHTML = `<span style="color: #ff7043;">Ошибка при анализе данных: ${aiioData.message}</span>`;
            }
        }
    })
    .catch(err => {
        responseBox.classList.remove('loading');
        responseBox.innerHTML = `<span style="color: #ff7043;">Ошибка: ${err.message}</span>`;
    });
}

// Вспомогательные функции для форматирования текста
function getReadableCategoryName(category) {
    const categories = {
        'all': 'Все категории',
        'ukraine': 'Украина',
        'middle_east': 'Ближний восток',
        'fake_news': 'Фейки',
        'info_war': 'Инфовойна',
        'europe': 'Европа',
        'usa': 'США',
        'other': 'Другое'
    };
    return categories[category] || category;
}

function getReadableTimePeriod(hours) {
    if (hours === 1) return '1 час';
    if (hours === 24) return '1 день';
    if (hours === 72) return '3 дня';
    if (hours === 168) return '1 неделю';
    if (hours === 720) return '1 месяц';
    return `${hours} часов`;
}