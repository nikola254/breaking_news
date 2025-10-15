// Начальное значение остатка токенов (можно будет получать с сервера)
const INITIAL_TOKEN_BALANCE = 998300;
const TOKEN_STORAGE_KEY = 'breaking_news_token_balance';
let currentTokenBalance = loadTokenBalance();

// Функция для загрузки баланса токенов из localStorage
function loadTokenBalance() {
    const savedBalance = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (savedBalance !== null) {
        const balance = parseInt(savedBalance);
        // Проверяем, что значение корректное
        if (!isNaN(balance) && balance >= 0) {
            return balance;
        }
    }
    return INITIAL_TOKEN_BALANCE;
}

// Функция для сохранения баланса токенов в localStorage
function saveTokenBalance(balance) {
    localStorage.setItem(TOKEN_STORAGE_KEY, balance.toString());
}

// Функция для сброса баланса токенов к начальному значению
function resetTokenBalance() {
    currentTokenBalance = INITIAL_TOKEN_BALANCE;
    saveTokenBalance(currentTokenBalance);
    updateTokenBalance(currentTokenBalance);
}

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
    
    // Добавляем кнопку сброса баланса токенов (если её нет)
    addResetTokenButton();
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
    
    // Сохраняем текущий баланс в localStorage
    currentTokenBalance = balance;
    saveTokenBalance(balance);
}

// Функция для добавления кнопки сброса баланса токенов
function addResetTokenButton() {
    const balanceElement = document.getElementById('tokens-balance');
    if (balanceElement && !document.getElementById('reset-tokens-btn')) {
        const resetButton = document.createElement('button');
        resetButton.id = 'reset-tokens-btn';
        resetButton.textContent = '↻';
        resetButton.title = 'Сбросить баланс токенов';
        resetButton.style.cssText = `
            margin-left: 10px;
            padding: 2px 8px;
            background: #2196f3;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            vertical-align: middle;
        `;
        
        resetButton.addEventListener('click', function() {
            if (confirm('Сбросить баланс токенов к начальному значению?')) {
                resetTokenBalance();
            }
        });
        
        balanceElement.parentNode.appendChild(resetButton);
    }
}

function sendToAI() {
    const prompt = document.getElementById('ai-prompt').value;
    const responseBox = document.getElementById('ai-response');
    const temperature = parseFloat(document.getElementById('temperature').value) || 0.7;
    const maxTokens = parseInt(document.getElementById('max_tokens').value) || 1000;
    const model = document.getElementById('ai-model').value;
    
    if (!prompt.trim()) {
        responseBox.innerHTML = '<span style="color: #ff7043;">Пожалуйста, введите запрос</span>';
        return;
    }
    
    // Показываем индикатор загрузки и текст "думаю..."
    responseBox.innerHTML = '<span class="thinking-text">Думаю...</span>';
    responseBox.classList.add('loading');
    
    // Используем только Cloud.ru API с моделью Qwen
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
        responseBox.innerHTML = `<span style="color: #ff7043;">Ошибка: ${err.message}</span>`;
    });

}

function displayChartsWithAnalysis(forecastData) {
    const chartContainer = document.getElementById('chart-container');
    if (!chartContainer) return;
    
    // Очищаем контейнер
    chartContainer.innerHTML = '';
    
    // Создаем контейнер для метаданных
    const metadataDiv = document.createElement('div');
    metadataDiv.className = 'analysis-metadata';
    metadataDiv.innerHTML = `
        <div class="metadata-grid">
            <div class="metadata-item">
                <span class="label">Категория:</span>
                <span class="value">${forecastData.metadata.category}</span>
            </div>
            <div class="metadata-item">
                <span class="label">Проанализировано новостей:</span>
                <span class="value">${forecastData.metadata.news_analyzed}</span>
            </div>
            <div class="metadata-item">
                <span class="label">Индекс напряженности:</span>
                <span class="value tension-index">${(forecastData.metadata.tension_index * 100).toFixed(1)}%</span>
            </div>
            <div class="metadata-item">
                <span class="label">Тренд:</span>
                <span class="value trend-${forecastData.tension.trend}">${forecastData.tension.trend}</span>
            </div>
        </div>
    `;
    chartContainer.appendChild(metadataDiv);
    
    // Создаем график напряженности
    const tensionChartDiv = document.createElement('div');
    tensionChartDiv.className = 'chart-section';
    tensionChartDiv.innerHTML = '<h3>Прогноз напряженности</h3><div id="tension-chart"></div>';
    chartContainer.appendChild(tensionChartDiv);
    
    // Отображаем график напряженности
    displayTensionChart(forecastData.tension.values);
    
    // Создаем график тем
    const topicsChartDiv = document.createElement('div');
    topicsChartDiv.className = 'chart-section';
    topicsChartDiv.innerHTML = '<h3>Ключевые темы</h3><div id="topics-chart"></div>';
    chartContainer.appendChild(topicsChartDiv);
    
    // Отображаем график тем
    displayTopicsChart(forecastData.topics);
    
    // Если есть военный прогноз, отображаем его
    if (forecastData.military_forecast) {
        displayMilitaryForecast(forecastData.military_forecast);
    }
}

function displayTensionChart(tensionValues) {
    const dates = tensionValues.map(item => item.date);
    const values = tensionValues.map(item => item.value);
    const lowerBounds = tensionValues.map(item => item.lower_bound);
    const upperBounds = tensionValues.map(item => item.upper_bound);
    
    const trace1 = {
        x: dates,
        y: values,
        type: 'scatter',
        mode: 'lines+markers',
        name: 'Прогноз напряженности',
        line: { color: '#e74c3c', width: 3 }
    };
    
    const trace2 = {
        x: dates,
        y: upperBounds,
        type: 'scatter',
        mode: 'lines',
        name: 'Верхняя граница',
        line: { color: 'rgba(231, 76, 60, 0.3)', width: 1 },
        showlegend: false
    };
    
    const trace3 = {
        x: dates,
        y: lowerBounds,
        type: 'scatter',
        mode: 'lines',
        name: 'Доверительный интервал',
        line: { color: 'rgba(231, 76, 60, 0.3)', width: 1 },
        fill: 'tonexty',
        fillcolor: 'rgba(231, 76, 60, 0.1)'
    };
    
    const layout = {
        title: 'Прогноз социальной напряженности',
        xaxis: { title: 'Дата' },
        yaxis: { title: 'Уровень напряженности', range: [0, 1] },
        showlegend: true
    };
    
    Plotly.newPlot('tension-chart', [trace3, trace2, trace1], layout);
}

function displayTopicsChart(topics) {
    const topicNames = topics.map(item => item.topic);
    const weights = topics.map(item => item.weight);
    
    const trace = {
        x: weights,
        y: topicNames,
        type: 'bar',
        orientation: 'h',
        marker: { color: '#3498db' }
    };
    
    const layout = {
        title: 'Ключевые темы в новостях',
        xaxis: { title: 'Вес темы' },
        yaxis: { title: 'Темы' },
        margin: { l: 150 }
    };
    
    Plotly.newPlot('topics-chart', [trace], layout);
}

function displayMilitaryForecast(militaryForecast) {
    const militaryDiv = document.createElement('div');
    militaryDiv.className = 'military-forecast-section';
    
    let actionsHtml = '';
    if (militaryForecast.probable_actions && militaryForecast.probable_actions.length > 0) {
        actionsHtml = `
            <div class="forecast-subsection">
                <h4>Вероятные действия:</h4>
                <ul>
                    ${militaryForecast.probable_actions.map(action => `<li>${action}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    let riskAreasHtml = '';
    if (militaryForecast.risk_areas && militaryForecast.risk_areas.length > 0) {
        riskAreasHtml = `
            <div class="forecast-subsection">
                <h4>Зоны риска:</h4>
                <ul>
                    ${militaryForecast.risk_areas.map(area => `<li>${area}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    militaryDiv.innerHTML = `
        <h3>Военно-стратегический прогноз</h3>
        <div class="military-assessment">
            <div class="assessment-grid">
                <div class="assessment-item">
                    <span class="label">Уровень напряженности:</span>
                    <span class="value">${militaryForecast.overall_assessment.tension_level}</span>
                </div>
                <div class="assessment-item">
                    <span class="label">Вероятность эскалации:</span>
                    <span class="value">${militaryForecast.overall_assessment.probability_escalation}%</span>
                </div>
                <div class="assessment-item">
                    <span class="label">Уровень риска:</span>
                    <span class="value risk-${militaryForecast.overall_assessment.risk_level}">${militaryForecast.overall_assessment.risk_level}</span>
                </div>
            </div>
        </div>
        ${actionsHtml}
        ${riskAreasHtml}
        <div class="forecast-subsection">
            <h4>Временные рамки:</h4>
            <p><strong>Краткосрочный прогноз:</strong> ${militaryForecast.timeline.short_term}</p>
            <p><strong>Среднесрочный прогноз:</strong> ${militaryForecast.timeline.medium_term}</p>
        </div>
    `;
    
    const chartContainer = document.getElementById('chart-container');
    chartContainer.appendChild(militaryDiv);
}

function displayCharts(data) {
    const chartContainer = document.getElementById('forecast-chart');
    
    // Отображаем график напряженности
    if (data.tension_chart_url) {
        console.log('Creating tension chart with URL:', data.tension_chart_url);
        const tensionChart = document.createElement('img');
        tensionChart.src = data.tension_chart_url;
        tensionChart.alt = 'График прогноза напряженности';
        tensionChart.className = 'forecast-chart-img';
        tensionChart.onload = function() {
            console.log('Tension chart loaded successfully');
        };
        tensionChart.onerror = function() {
            console.error('Failed to load tension chart:', this.src);
        };
        chartContainer.appendChild(tensionChart);
    }
    
    // Убираем отображение графика тем - не нужен
}

// Функция для автоматического заполнения примеров запросов
function fillPromptExamples() {
    const promptTextarea = document.getElementById('ai-prompt');
    const category = document.getElementById('news-category').value;
    
    // Примеры запросов в зависимости от категории
    const examples = {
        'military_operations': [
            "Проанализируй влияние последних военных операций на социальную напряженность. Какие факторы могут привести к эскалации конфликта?",
            "Оцени риски дальнейшего развития военных действий. Какие сценарии наиболее вероятны в ближайшие дни?",
            "Проанализируй эффективность военных стратегий и их влияние на общественное мнение."
        ],
        'humanitarian_crisis': [
            "Оцени масштабы гуманитарного кризиса и его влияние на социальную стабильность. Какие меры необходимы для улучшения ситуации?",
            "Проанализируй доступность гуманитарной помощи и эффективность её распределения.",
            "Какие долгосрочные последствия гуманитарного кризиса для региона?"
        ],
        'economic_consequences': [
            "Проанализируй экономические последствия конфликта и их влияние на социальную напряженность.",
            "Оцени риски экономической нестабильности и возможные меры по стабилизации.",
            "Какие секторы экономики наиболее уязвимы и требуют особого внимания?"
        ],
        'political_decisions': [
            "Проанализируй влияние политических решений на развитие ситуации. Какие шаги могут снизить напряженность?",
            "Оцени эффективность дипломатических усилий и перспективы мирного урегулирования.",
            "Какие политические факторы могут привести к эскалации или деэскалации конфликта?"
        ],
        'information_social': [
            "Проанализируй влияние информационной войны на общественное мнение и социальную стабильность.",
            "Оцени роль социальных сетей в распространении информации и формировании повестки дня.",
            "Какие меры необходимы для противодействия дезинформации и манипуляциям?"
        ],
        'all': [
            "Проанализируй общую ситуацию и дай комплексный прогноз развития событий на ближайшие дни.",
            "Оцени все ключевые факторы влияния и их взаимосвязь. Какие сценарии наиболее вероятны?",
            "Дай рекомендации по снижению социальной напряженности и стабилизации ситуации."
        ]
    };
    
    // Получаем примеры для текущей категории
    const categoryExamples = examples[category] || examples['all'];
    
    // Выбираем случайный пример
    const randomExample = categoryExamples[Math.floor(Math.random() * categoryExamples.length)];
    
    // Заполняем поле
    promptTextarea.value = randomExample;
    
    // Добавляем визуальный эффект
    promptTextarea.style.backgroundColor = '#e8f5e8';
    setTimeout(() => {
        promptTextarea.style.backgroundColor = 'white';
    }, 1000);
    
    // Показываем уведомление
    showNotification('✅ Пример запроса заполнен!', 'success');
}

// Функция для показа уведомлений
function showNotification(message, type = 'info') {
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'success' ? '#4caf50' : '#2196f3'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 1000;
        font-size: 14px;
        font-weight: 500;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Анимация появления
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Автоматическое скрытие
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}
function generateForecast() {
    const category = document.getElementById('news-category').value;
    const analysisPeriod = parseInt(document.getElementById('analysis-period').value);
    const forecastPeriod = parseInt(document.getElementById('forecast-period').value);
    const aiPrompt = document.getElementById('ai-prompt').value;
    
    const responseBox = document.getElementById('ai-response');
    const chartContainer = document.getElementById('forecast-chart');
    
    // Показываем индикатор загрузки
    responseBox.innerHTML = '<span class="thinking-text">🤖 Отправляю запрос к AI для генерации прогноза...</span>';
    responseBox.classList.add('loading');
    chartContainer.innerHTML = '';
    
    // Вызов API прогнозирования
    fetch('/api/forecast/generate_forecast', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            category: category,
            analysis_period: analysisPeriod,
            forecast_period: forecastPeriod,
            prompt: aiPrompt
        })
    })
    .then(res => res.json())
    .then(data => {
        responseBox.classList.remove('loading');
        
        if (data.status === 'success') {
            // Отображение результата прогноза
            displayForecastResult(data);
            
            // Генерация графиков только если есть данные
            if (data.forecast_data && data.forecast_data.tension_forecast) {
                generateCharts(data.forecast_data, category);
            }
        } else {
            responseBox.innerHTML = `<span style="color: #ff7043;">Ошибка: ${data.message}</span>`;
        }
    })
    .catch(error => {
        responseBox.classList.remove('loading');
        responseBox.innerHTML = `<span style="color: #ff7043;">Ошибка: ${error.message}</span>`;
    });
}

function parseMarkdown(text) {
    if (!text) return '';
    
    // Сначала экранируем HTML
    let result = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // Затем применяем markdown форматирование
    result = result
        // Заголовки (должны быть в начале строки) - обрабатываем от большего к меньшему
        .replace(/^##### (.+)$/gim, '<h5>$1</h5>')
        .replace(/^#### (.+)$/gim, '<h4>$1</h4>')
        .replace(/^### (.+)$/gim, '<h3>$1</h3>')
        .replace(/^## (.+)$/gim, '<h2>$1</h2>')
        .replace(/^# (.+)$/gim, '<h1>$1</h1>')
        // Жирный текст
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Курсив (только одиночные звездочки, не в жирном тексте)
        .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, '<em>$1</em>')
        // Списки - сначала собираем все элементы списка
        .replace(/^[\-\*] (.+)$/gim, '<li>$1</li>')
        // Оборачиваем последовательные <li> в <ul>
        .replace(/(<li>[\s\S]+?<\/li>)(?!\s*<li>)/g, function(match) {
            // Проверяем, не обернут ли уже в ul
            if (!match.startsWith('<ul>')) {
                return '<ul>' + match + '</ul>';
            }
            return match;
        })
        // Переносы строк (но не внутри тегов)
        .replace(/\n(?![<])/g, '<br>');
    
    return result;
}

function displayForecastResult(data) {
    const responseBox = document.getElementById('ai-response');
    
    // Функция для очистки текста от лишних пробелов и пустых строк
    function cleanText(text) {
        if (!text) return '';
        
        return text
            // Убираем множественные пустые строки (2+ подряд заменяем на 1)
            .replace(/\n{2,}/g, '\n')
            // Убираем trailing whitespace в конце каждой строки
            .replace(/[ \t]+$/gm, '')
            // Убираем строки состоящие только из пробелов
            .replace(/^\s*$/gm, '')
            // Убираем множественные пустые строки после предыдущих операций
            .replace(/\n{2,}/g, '\n')
            // Убираем trailing whitespace в конце всего текста
            .trim();
    }
    
    // Форматирование и отображение результата прогноза
    let resultHtml = '';
    
    // Приоритет: AI прогноз, затем стандартный формат
    if (data.forecast_data && data.forecast_data.ai_forecast) {
        // Очищаем и отображаем детальный AI прогноз
        const cleanedForecast = cleanText(data.forecast_data.ai_forecast);
        const formattedForecast = parseMarkdown(cleanedForecast);
        resultHtml += `<div class="forecast-section ai-forecast">
            <div class="ai-response">${formattedForecast}</div>
        </div>`;
        
        // Добавляем метаданные AI
        if (data.metadata) {
            resultHtml += `<div class="forecast-section">
                <h4>🔧 Техническая информация</h4>
                <div class="forecast-stats">`;
            
            if (data.metadata.ai_api_used) {
                resultHtml += `<div class="stat-item">
                    <strong>🤖 AI модель:</strong> ${data.metadata.ai_api_used}
                </div>`;
            }
            
            if (data.metadata.ai_tokens_used) {
                resultHtml += `<div class="stat-item">
                    <strong>📊 Использовано токенов:</strong> ${data.metadata.ai_tokens_used}
                </div>`;
            }
            
            if (data.metadata.news_analyzed) {
                resultHtml += `<div class="stat-item">
                    <strong>📰 Проанализировано новостей:</strong> ${data.metadata.news_analyzed}
                </div>`;
            }
            
            resultHtml += `</div></div>`;
        }
    } else if (data.forecast_data) {
        // Fallback на старый формат если нет AI прогноза
        const forecast = data.forecast_data;
        
        // Отображаем анализ
        if (forecast.analysis) {
            resultHtml += `<div class="forecast-section">
                <h4>📊 Анализ текущей ситуации</h4>
                <p>${forecast.analysis}</p>
            </div>`;
        }
        
        // Отображаем прогноз
        if (forecast.forecast) {
            resultHtml += `<div class="forecast-section">
                <h4>🔮 Прогноз развития</h4>
                <p>${forecast.forecast}</p>
            </div>`;
        }
        
        // Отображаем ключевые факторы
        if (forecast.key_factors) {
            resultHtml += `<div class="forecast-section">
                <h4>⚡ Ключевые факторы влияния</h4>
                <ul>`;
            forecast.key_factors.forEach(factor => {
                resultHtml += `<li>${factor}</li>`;
            });
            resultHtml += `</ul></div>`;
        }
        
        // Отображаем сценарии
        if (forecast.scenarios) {
            resultHtml += `<div class="forecast-section">
                <h4>🎯 Возможные сценарии</h4>
                <ul>`;
            forecast.scenarios.forEach(scenario => {
                resultHtml += `<li>${scenario}</li>`;
            });
            resultHtml += `</ul></div>`;
        }
        
        // Отображаем статистику
        if (forecast.statistics) {
            resultHtml += `<div class="forecast-section">
                <h4>📈 Статистика</h4>
                <div class="forecast-stats">`;
            
            if (forecast.statistics.historical_points) {
                resultHtml += `<div class="stat-item">
                    <strong>📊 Исторических точек:</strong> ${forecast.statistics.historical_points}
                </div>`;
            }
            
            if (forecast.statistics.forecast_points) {
                resultHtml += `<div class="stat-item">
                    <strong>🔮 Прогнозных точек:</strong> ${forecast.statistics.forecast_points}
                </div>`;
            }
            
            if (forecast.statistics.average_tension) {
                resultHtml += `<div class="stat-item">
                    <strong>📈 Средняя напряженность:</strong> ${forecast.statistics.average_tension}%
                </div>`;
            }
            
            if (forecast.statistics.trend) {
                resultHtml += `<div class="stat-item">
                    <strong>📉 Тренд:</strong> ${forecast.statistics.trend}
                </div>`;
            }
            
            resultHtml += `</div></div>`;
        }
    }
    
    // Если есть дополнительный AI ответ на пользовательский запрос, добавляем его в конец
    if (data.ai_response) {
        const cleanedResponse = cleanText(data.ai_response);
        const formattedResponse = parseMarkdown(cleanedResponse);
        resultHtml += `<div class="forecast-section user-query-response">
            <h4>📝 Ответ на ваш запрос</h4>
            <div class="ai-response">${formattedResponse}</div>
        </div>`;
    }
    
    // Если нет данных для отображения, показываем сообщение
    if (!resultHtml) {
        resultHtml = '<p style="color: #ff7043;">⚠️ Не удалось получить данные для прогноза. Проверьте настройки API.</p>';
    }
    
    responseBox.innerHTML = resultHtml;
}

function generateCharts(forecastData, category) {
    const chartContainer = document.getElementById('forecast-chart');
    
    // Вызов API для генерации графиков
    fetch('/api/chart/generate_charts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            forecast_data: forecastData,
            category: category
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            // Отображение графиков
            displayCharts(data);
        } else {
            console.error('Ошибка генерации графиков:', data.message);
        }
    })
    .catch(error => {
        console.error('Ошибка при генерации графиков:', error);
    });
}

// Функция для генерации графиков на основе ответа AI
function generateChartsFromAIResponse(aiResponse, category, forecastPeriod) {
    // Пытаемся извлечь числовые данные из ответа AI
    // Если AI предоставил структурированные данные, используем их
    // Иначе генерируем данные на основе анализа текста
    
    let forecastData;
    try {
        // Пытаемся найти JSON в ответе AI
        const jsonMatch = aiResponse.match(/\{[^}]*"tension"[^}]*\}/g) || 
                         aiResponse.match(/\{[^}]*"forecast"[^}]*\}/g);
        
        if (jsonMatch) {
            forecastData = JSON.parse(jsonMatch[0]);
        } else {
            // Если JSON не найден, анализируем текст на предмет числовых значений
            forecastData = extractForecastFromText(aiResponse, category, forecastPeriod);
        }
    } catch (e) {
        // Если парсинг не удался, создаем данные на основе анализа текста
        forecastData = extractForecastFromText(aiResponse, category, forecastPeriod);
    }
    
    // Отправляем данные на сервер для создания графиков с реальным анализом
    return fetch('/api/generate_charts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            forecast_data: forecastData,
            category: category,
            ai_response: aiResponse,
            analysis_period: parseInt(document.getElementById('analysis-period').value),
            forecast_period: parseInt(document.getElementById('forecast-period').value)
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            return {
                tension_chart_url: data.tension_chart_url,
                topics_chart_url: data.topics_chart_url
            };
        } else {
            throw new Error(data.message || 'Ошибка при создании графиков');
        }
    });
}

// Функция для извлечения данных прогноза из текста AI
function extractForecastFromText(text, category, forecastPeriod) {
    const today = new Date();
    const forecastDays = Math.max(1, Math.floor(forecastPeriod / 24));
    
    // Анализируем текст на предмет ключевых слов для определения уровня напряженности
    const tensionKeywords = {
        high: ['высок', 'критич', 'опасн', 'тревожн', 'напряж', 'конфликт', 'кризис'],
        medium: ['умерен', 'средн', 'стабильн', 'нейтральн'],
        low: ['низк', 'спокойн', 'мирн', 'позитивн']
    };
    
    let baseTension = 0.5; // По умолчанию средний уровень
    
    const lowerText = text.toLowerCase();
    let highCount = 0, mediumCount = 0, lowCount = 0;
    
    tensionKeywords.high.forEach(word => {
        if (lowerText.includes(word)) highCount++;
    });
    tensionKeywords.medium.forEach(word => {
        if (lowerText.includes(word)) mediumCount++;
    });
    tensionKeywords.low.forEach(word => {
        if (lowerText.includes(word)) lowCount++;
    });
    
    if (highCount > mediumCount && highCount > lowCount) {
        baseTension = 0.7 + Math.random() * 0.2;
    } else if (lowCount > mediumCount && lowCount > highCount) {
        baseTension = 0.2 + Math.random() * 0.2;
    } else {
        baseTension = 0.4 + Math.random() * 0.2;
    }
    
    // Генерируем данные прогноза
    const tensionValues = [];
    const trend = (Math.random() - 0.5) * 0.1; // Случайный тренд
    
    for (let i = 0; i < forecastDays; i++) {
        const date = new Date(today);
        date.setDate(date.getDate() + i);
        
        const noise = (Math.random() - 0.5) * 0.1;
        const trendComponent = trend * i / forecastDays;
        const value = Math.min(1.0, Math.max(0.1, baseTension + noise + trendComponent));
        
        tensionValues.push({
            date: date.toLocaleDateString('ru-RU'),
            value: value,
            lower_bound: Math.max(0.1, value - 0.05 - Math.random() * 0.05),
            upper_bound: Math.min(1.0, value + 0.05 + Math.random() * 0.05)
        });
    }
    
    // Генерируем данные по темам на основе категории
    const topicsByCategory = {
        'ukraine': [
            { name: 'Военные действия', value: 0.4 + Math.random() * 0.2, change: (Math.random() - 0.5) * 0.1 },
            { name: 'Дипломатия', value: 0.2 + Math.random() * 0.1, change: (Math.random() - 0.5) * 0.1 },
            { name: 'Гуманитарная ситуация', value: 0.1 + Math.random() * 0.1, change: (Math.random() - 0.5) * 0.1 },
            { name: 'Экономика', value: 0.05 + Math.random() * 0.1, change: (Math.random() - 0.5) * 0.05 }
        ],
        'middle_east': [
            { name: 'Конфликт Израиль-Палестина', value: 0.3 + Math.random() * 0.2, change: (Math.random() - 0.5) * 0.1 },
            { name: 'Иран', value: 0.2 + Math.random() * 0.1, change: (Math.random() - 0.5) * 0.1 },
            { name: 'Сирия', value: 0.1 + Math.random() * 0.1, change: (Math.random() - 0.5) * 0.1 },
            { name: 'Йемен', value: 0.05 + Math.random() * 0.1, change: (Math.random() - 0.5) * 0.05 }
        ]
    };
    
    const defaultTopics = [
        { name: 'Политика', value: 0.2 + Math.random() * 0.2, change: (Math.random() - 0.5) * 0.1 },
        { name: 'Экономика', value: 0.1 + Math.random() * 0.2, change: (Math.random() - 0.5) * 0.1 },
        { name: 'Военные действия', value: 0.2 + Math.random() * 0.3, change: (Math.random() - 0.5) * 0.1 },
        { name: 'Международные отношения', value: 0.1 + Math.random() * 0.1, change: (Math.random() - 0.5) * 0.1 }
    ];
    
    const topics = topicsByCategory[category] || defaultTopics;
    
    return {
        tension_forecast: {
            values: tensionValues
        },
        topics_forecast: {
            topics: topics
        }
    };

}

// Вспомогательные функции для форматирования текста
function getReadableCategoryName(category) {
    const categories = {
        'all': 'Все категории',
        'military_operations': 'Военные операции',
    'humanitarian_crisis': 'Гуманитарный кризис',
    'economic_consequences': 'Экономические последствия',
    'political_decisions': 'Политические решения',
    'information_social': 'Информационно-социальные аспекты'
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