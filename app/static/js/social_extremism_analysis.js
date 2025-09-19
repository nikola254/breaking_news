// JavaScript для обработки форм и взаимодействия
document.addEventListener('DOMContentLoaded', function() {
    
    // Инициализация
    loadInitialData();
    
    // Анализ аккаунта
    document.getElementById('accountAnalysisForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const button = document.getElementById('startAccountAnalysis');
        const spinner = button.querySelector('.spinner-border');
        const resultsDiv = document.getElementById('accountResults');
        const resultsContent = document.getElementById('accountResultsContent');
        
        // Показать спиннер
        spinner.classList.remove('d-none');
        button.disabled = true;
        
        const formData = new FormData(this);
        
        fetch('/social-analysis/analyze-account', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resultsContent.innerHTML = formatAccountResults(data.results);
                resultsDiv.classList.remove('d-none');
            } else {
                alert('Ошибка: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Произошла ошибка при анализе');
        })
        .finally(() => {
            spinner.classList.add('d-none');
            button.disabled = false;
        });
    });
    
    // Поиск по ключевым словам
    document.getElementById('keywordSearchForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const button = document.getElementById('startKeywordSearch');
        const spinner = button.querySelector('.spinner-border');
        const resultsDiv = document.getElementById('keywordResults');
        const resultsContent = document.getElementById('keywordResultsContent');
        
        // Показать спиннер
        spinner.classList.remove('d-none');
        button.disabled = true;
        
        const formData = new FormData(this);
        
        fetch('/social-analysis/search-keywords', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                resultsContent.innerHTML = formatSearchResults(data.results);
                resultsDiv.classList.remove('d-none');
            } else {
                alert('Ошибка: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Произошла ошибка при поиске');
        })
        .finally(() => {
            spinner.classList.add('d-none');
            button.disabled = false;
        });
    });
    
    // Мониторинг
    document.getElementById('monitoringForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const button = document.getElementById('startMonitoring');
        const spinner = button.querySelector('.spinner-border');
        
        // Показать спиннер
        spinner.classList.remove('d-none');
        button.disabled = true;
        
        const formData = new FormData(this);
        
        fetch('/social-analysis/start-monitoring', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Мониторинг запущен успешно');
                loadActiveSessions();
                this.reset();
            } else {
                alert('Ошибка: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Произошла ошибка при запуске мониторинга');
        })
        .finally(() => {
            spinner.classList.add('d-none');
            button.disabled = false;
        });
    });
    
    // Фильтры аналитики
    document.getElementById('analyticsFiltersForm').addEventListener('submit', function(e) {
        e.preventDefault();
        loadAnalytics();
    });
    
    // Фильтры контента
    document.getElementById('contentFiltersForm').addEventListener('submit', function(e) {
        e.preventDefault();
        loadContent();
    });
    
    // Добавление источника
    document.getElementById('addSourceForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        fetch('/social-analysis/add-source', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Источник добавлен успешно');
                loadSources();
                this.reset();
            } else {
                alert('Ошибка: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Произошла ошибка при добавлении источника');
        });
    });
    
    // Обновление слайдера уверенности
    document.getElementById('analyticsConfidence').addEventListener('input', function() {
        const value = Math.round(this.value * 100);
        this.nextElementSibling.textContent = value + '%';
    });
});

// Функции для загрузки данных
function loadInitialData() {
    loadActiveSessions();
    loadAnalytics();
    loadSources();
}

function loadActiveSessions() {
    fetch('/social-analysis/monitoring-sessions')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('activeSessions');
            if (data.sessions && data.sessions.length > 0) {
                container.innerHTML = formatActiveSessions(data.sessions);
            } else {
                container.innerHTML = '<p class="text-muted">Нет активных сессий мониторинга</p>';
            }
        })
        .catch(error => {
            console.error('Error loading sessions:', error);
        });
}

function loadAnalytics() {
    const formData = new FormData(document.getElementById('analyticsFiltersForm'));
    const params = new URLSearchParams(formData);
    
    fetch('/social-analysis/statistics?' + params)
        .then(response => response.json())
        .then(data => {
            updateStatistics(data);
            updateCharts(data);
            updateChannelsTable(data.channels || []);
        })
        .catch(error => {
            console.error('Error loading analytics:', error);
        });
}

function loadContent() {
    const formData = new FormData(document.getElementById('contentFiltersForm'));
    const params = new URLSearchParams(formData);
    
    const contentList = document.getElementById('contentList');
    contentList.innerHTML = '<div class="loading-spinner"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Загрузка контента...</p></div>';
    
    fetch('/social-analysis/results?' + params)
        .then(response => response.json())
        .then(data => {
            if (data.results && data.results.length > 0) {
                contentList.innerHTML = formatContentList(data.results);
                updatePagination(data.pagination || {});
            } else {
                contentList.innerHTML = '<p class="text-muted text-center">Контент не найден</p>';
            }
        })
        .catch(error => {
            console.error('Error loading content:', error);
            contentList.innerHTML = '<p class="text-danger text-center">Ошибка загрузки контента</p>';
        });
}

function loadSources() {
    fetch('/social-analysis/sources')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('sourcesTableBody');
            if (data.sources && data.sources.length > 0) {
                tbody.innerHTML = formatSourcesTable(data.sources);
            } else {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted">Нет добавленных источников</td></tr>';
            }
        })
        .catch(error => {
            console.error('Error loading sources:', error);
        });
}

// Функции форматирования данных
function formatAccountResults(results) {
    let html = '<div class="row">';
    
    // Общая статистика
    html += '<div class="col-md-12"><h6>Общая статистика</h6>';
    html += '<ul class="list-group list-group-flush">';
    html += `<li class="list-group-item">Платформа: <strong>${results.platform}</strong></li>`;
    html += `<li class="list-group-item">Проанализировано постов: <span class="badge bg-primary">${results.posts_analyzed || 0}</span></li>`;
    html += `<li class="list-group-item">Экстремистский контент: <span class="badge bg-danger">${results.extremist_content_count || 0}</span></li>`;
    html += `<li class="list-group-item">Подозрительный контент: <span class="badge bg-warning">${results.suspicious_content_count || 0}</span></li>`;
    html += `<li class="list-group-item">Нормальный контент: <span class="badge bg-success">${results.normal_content_count || 0}</span></li>`;
    html += '</ul></div>';
    
    // Детальные результаты
    if (results.detailed_results && results.detailed_results.length > 0) {
        html += '<div class="col-md-12 mt-3"><h6>Детальные результаты</h6>';
        html += '<div class="table-responsive">';
        html += '<table class="table table-sm">';
        html += '<thead><tr><th class="text-center" style="width: 50%;">Контент</th><th class="text-center" style="width: 20%;">Классификация</th><th class="text-center" style="width: 15%;">Уверенность</th><th class="text-center" style="width: 15%;">Ключевые слова</th></tr></thead>';
        html += '<tbody>';
        
        results.detailed_results.forEach(item => {
            const badgeClass = getBadgeClass(item.classification);
            const confidence = Math.round((item.confidence || 0) * 100);
            const keywords = Array.isArray(item.keywords) ? item.keywords.join(', ') : (item.keywords || '');
            const translatedClassification = translateClassification(item.classification);
            
            // Определяем класс для цветового выделения контента
            let contentClass = 'normal-content';
            if (item.classification === 'suspicious') {
                contentClass = 'suspicious-content';
            } else if (item.classification === 'extremist') {
                contentClass = 'extremist-content';
            }
            
            html += '<tr>';
            html += `<td><div class="${contentClass} content-text-center" style="word-wrap: break-word; width: 100%;" title="Нажмите для просмотра полного текста" onclick="showFullContent('${encodeURIComponent(item.content || '')}')">${item.content || ''}</div></td>`;
            html += `<td class="text-center"><span class="badge ${badgeClass}">${translatedClassification}</span></td>`;
            html += `<td class="text-center">${confidence}%</td>`;
            html += `<td class="text-center"><small>${keywords}</small></td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table></div></div>';
    }
    
    html += '</div>';
    return html;
}

function formatSearchResults(results) {
    if (!results || results.length === 0) {
        return '<p class="text-muted text-center">Результаты не найдены</p>';
    }
    
    let html = '<div class="row">';
    
    results.forEach((result, index) => {
        const badgeClass = getBadgeClass(result.classification);
        const confidence = Math.round((result.confidence || 0) * 100);
        const shortContent = result.content; // Показываем полный контент
        const highlightedContent = highlightExtremistPhrases(result.content, result.extremist_keywords || []);
        const isLongContent = false; // Отключаем сворачивание контента
        const translatedClassification = translateClassification(result.classification);
        
        // Определяем класс для цветового выделения карточки
        let cardClass = 'card content-card';
        if (result.classification === 'suspicious') {
            cardClass += ' border-warning';
        } else if (result.classification === 'extremist') {
            cardClass += ' border-danger';
        } else {
            cardClass += ' border-success';
        }
        
        html += '<div class="col-md-6 mb-3">';
        html += `<div class="${cardClass}">`;
        html += '<div class="card-body">';
        html += `<h6 class="card-title text-center">${result.platform} - ${result.author || 'Неизвестный автор'}</h6>`;
        
        // Краткий контент
        html += `<div id="short-content-${index}" class="card-text">`;
        html += highlightExtremistPhrases(shortContent, result.extremist_keywords || []);
        if (isLongContent) {
            html += `<span class="text-primary" style="cursor: pointer;" onclick="toggleContent(${index})"> ...показать полностью</span>`;
        }
        html += '</div>';
        
        // Полный контент (скрытый)
        if (isLongContent) {
            html += `<div id="full-content-${index}" class="card-text" style="display: none;">`;
            html += highlightedContent;
            html += `<span class="text-primary" style="cursor: pointer;" onclick="toggleContent(${index})"> свернуть</span>`;
            html += '</div>';
        }
        
        html += `<div class="d-flex justify-content-between align-items-center mt-3">`;
        html += `<span class="badge ${badgeClass}">${translatedClassification}</span>`;
        html += `<small class="text-muted">Уверенность: ${confidence}%</small>`;
        html += '</div>';
        html += '</div></div></div>';
    });
    
    html += '</div>';
    return html;
}

function formatActiveSessions(sessions) {
    let html = '<div class="table-responsive">';
    html += '<table class="table table-sm">';
    html += '<thead><tr><th class="text-center">Название</th><th class="text-center">Платформа</th><th class="text-center">Статус</th><th class="text-center">Интервал</th><th class="text-center">Действия</th></tr></thead>';
    html += '<tbody>';
    
    sessions.forEach(session => {
        html += '<tr>';
        html += `<td class="text-center">${session.name}</td>`;
        html += `<td class="text-center">${session.platform}</td>`;
        html += `<td class="text-center"><span class="badge ${session.status === 'active' ? 'bg-success' : 'bg-secondary'}">${session.status}</span></td>`;
        html += `<td class="text-center">${session.interval} мин</td>`;
        html += `<td class="text-center"><button class="btn btn-sm btn-danger" onclick="stopMonitoring('${session.id}')">Остановить</button></td>`;
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    return html;
}

function formatContentList(content) {
    let html = '';
    
    content.forEach((item, index) => {
        const badgeClass = getBadgeClass(item.classification);
        const confidence = Math.round((item.confidence || 0) * 100);
        const date = new Date(item.analysis_date).toLocaleString('ru-RU');
        const shortContent = item.content; // Показываем полный контент
        const highlightedContent = highlightExtremistPhrases(item.content, item.extremist_keywords || []);
        const isLongContent = false; // Отключаем сворачивание контента
        const contentId = `content-list-${index}`;
        const translatedClassification = translateClassification(item.classification);
        
        // Определяем класс для цветового выделения карточки
        let cardClass = 'card content-card mb-3';
        if (item.classification === 'suspicious') {
            cardClass += ' border-warning';
        } else if (item.classification === 'extremist') {
            cardClass += ' border-danger';
        } else {
            cardClass += ' border-success';
        }
        
        html += `<div class="${cardClass}">`;
        html += '<div class="card-body">';
        html += '<div class="row">';
        html += '<div class="col-md-8">';
        html += `<h6 class="card-title text-center">${item.platform} - ${item.author || 'Неизвестный автор'}</h6>`;
        
        // Краткий контент
        html += `<div id="short-${contentId}" class="card-text">`;
        html += highlightExtremistPhrases(shortContent, item.extremist_keywords || []);
        if (isLongContent) {
            html += `<span class="text-primary" style="cursor: pointer;" onclick="toggleContentList('${contentId}')"> ...показать полностью</span>`;
        }
        html += '</div>';
        
        // Полный контент (скрытый)
        if (isLongContent) {
            html += `<div id="full-${contentId}" class="card-text" style="display: none;">`;
            html += highlightedContent;
            html += `<span class="text-primary" style="cursor: pointer;" onclick="toggleContentList('${contentId}')"> свернуть</span>`;
            html += '</div>';
        }
        
        html += `<small class="text-muted d-block text-center mt-2">Дата анализа: ${date}</small>`;
        html += '</div>';
        html += '<div class="col-md-4 text-center">';
        html += `<span class="badge ${badgeClass} mb-2">${translatedClassification}</span><br>`;
        html += `<small>Уверенность: ${confidence}%</small><br>`;
        html += `<button class="btn btn-sm btn-outline-primary mt-2" onclick="showContentDetails('${item.id}')">Подробнее</button>`;
        html += '</div>';
        html += '</div>';
        html += '</div></div>';
    });
    
    return html;
}

function formatSourcesTable(sources) {
    let html = '';
    
    sources.forEach(source => {
        const statusBadge = source.status === 'active' ? 'bg-success' : 'bg-secondary';
        const lastCheck = source.last_check ? new Date(source.last_check).toLocaleString('ru-RU') : 'Никогда';
        
        html += '<tr>';
        html += `<td class="text-center">${source.name}</td>`;
        html += `<td class="text-center"><i class="platform-${source.platform}"></i> ${source.platform}</td>`;
        html += `<td class="text-center"><a href="${source.url}" target="_blank">${truncateText(source.url, 50)}</a></td>`;
        html += `<td class="text-center"><span class="badge ${statusBadge}">${source.status}</span></td>`;
        html += `<td class="text-center">${lastCheck}</td>`;
        html += `<td class="text-center">${source.content_found || 0}</td>`;
        html += `<td class="text-center">
                    <button class="btn btn-sm btn-outline-primary me-1" onclick="checkSource('${source.id}')">Проверить</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="removeSource('${source.id}')">Удалить</button>
                 </td>`;
        html += '</tr>';
    });
    
    return html;
}

function updateStatistics(data) {
    document.getElementById('totalAnalyzed').textContent = data.total_analyzed || 0;
    document.getElementById('totalExtremist').textContent = data.total_extremist || 0;
    document.getElementById('totalHateSpeech').textContent = data.total_hate_speech || 0;
    document.getElementById('totalPropaganda').textContent = data.total_propaganda || 0;
    document.getElementById('uniqueSources').textContent = data.unique_sources || 0;
    document.getElementById('extremistPercentage').textContent = (data.extremist_percentage || 0) + '%';
}

function updateCharts(data) {
    // Обновление графиков с помощью Chart.js
    // Здесь будет код для обновления графиков
}

function updateChannelsTable(channels) {
    const tbody = document.getElementById('channelsTableBody');
    if (channels.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Нет данных</td></tr>';
        return;
    }
    
    let html = '';
    channels.forEach(channel => {
        const riskLevel = calculateRiskLevel(channel);
        const riskBadge = getRiskBadgeClass(riskLevel);
        const lastActivity = channel.last_activity ? new Date(channel.last_activity).toLocaleString('ru-RU') : 'Неизвестно';
        
        html += '<tr>';
        html += `<td>${channel.name || channel.url}</td>`;
        html += `<td><i class="platform-${channel.platform}"></i> ${channel.platform}</td>`;
        html += `<td>${channel.total_posts || 0}</td>`;
        html += `<td>${channel.extremist_count || 0}</td>`;
        html += `<td>${channel.hate_speech_count || 0}</td>`;
        html += `<td>${channel.propaganda_count || 0}</td>`;
        html += `<td><span class="badge ${riskBadge}">${riskLevel}</span></td>`;
        html += `<td>${lastActivity}</td>`;
        html += '</tr>';
    });
    
    tbody.innerHTML = html;
}

function updatePagination(pagination) {
    // Обновление пагинации
    const container = document.getElementById('contentPagination');
    // Здесь будет код для генерации пагинации
}

// Вспомогательные функции
function getBadgeClass(classification) {
    switch (classification) {
        case 'extremist': return 'badge-extremist';
        case 'suspicious': return 'badge-suspicious';
        case 'hate_speech': return 'badge-hate-speech';
        case 'propaganda': return 'badge-propaganda';
        case 'normal': return 'badge-normal';
        default: return 'badge-normal';
    }
}

function translateClassification(classification) {
    switch (classification) {
        case 'extremist': return 'экстремистский';
        case 'suspicious': return 'подозрительный';
        case 'hate_speech': return 'разжигание ненависти';
        case 'propaganda': return 'пропаганда';
        case 'normal': return 'обычный';
        default: return 'неизвестно';
    }
}

function getRiskBadgeClass(riskLevel) {
    switch (riskLevel) {
        case 'Критический': return 'bg-danger';
        case 'Высокий': return 'bg-warning';
        case 'Средний': return 'bg-info';
        default: return 'bg-success';
    }
}

function calculateRiskLevel(channel) {
    const total = channel.total_posts || 1;
    const extremist = channel.extremist_count || 0;
    const percentage = (extremist / total) * 100;
    
    if (percentage > 50) return 'Критический';
    if (percentage > 20) return 'Высокий';
    if (percentage > 5) return 'Средний';
    return 'Низкий';
}

// Функции действий
function stopMonitoring(sessionId) {
    if (confirm('Остановить мониторинг?')) {
        fetch(`/social-analysis/stop-monitoring/${sessionId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadActiveSessions();
            } else {
                alert('Ошибка: ' + data.error);
            }
        });
    }
}

function checkSource(sourceId) {
    fetch(`/social-analysis/check-source/${sourceId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Проверка источника запущена');
            loadSources();
        } else {
            alert('Ошибка: ' + data.error);
        }
    });
}

function removeSource(sourceId) {
    if (confirm('Удалить источник?')) {
        fetch(`/social-analysis/remove-source/${sourceId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                loadSources();
            } else {
                alert('Ошибка: ' + data.error);
            }
        });
    }
}

function showContentDetails(contentId) {
    fetch(`/social-analysis/content/${contentId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                document.getElementById('modalContentBody').innerHTML = formatContentDetails(data.content);
                new bootstrap.Modal(document.getElementById('contentModal')).show();
            }
        });
}

function showFullContent(encodedContent) {
    const content = decodeURIComponent(encodedContent);
    const modalHtml = `
        <div class="modal fade" id="fullContentModal" tabindex="-1" aria-labelledby="fullContentModalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="fullContentModalLabel">Полный текст поста</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Закрыть"></button>
                    </div>
                    <div class="modal-body" style="max-height: 75vh; overflow-y: auto;">
                        <div style="color: #000; background-color: #fff; padding: 20px; border-radius: 8px; text-align: left; line-height: 1.6; font-size: 16px; white-space: normal; word-wrap: break-word; overflow-wrap: break-word;">
                            ${content.replace(/\s+/g, ' ').trim()}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Удаляем предыдущее модальное окно, если оно есть
    const existingModal = document.getElementById('fullContentModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Добавляем новое модальное окно
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Показываем модальное окно
    const modal = new bootstrap.Modal(document.getElementById('fullContentModal'));
    modal.show();
}

function formatContentDetails(content) {
    // Форматирование детальной информации о контенте
    const highlightedContent = highlightExtremistPhrases(content.content, content.extremist_keywords || []);
    const translatedClassification = translateClassification(content.classification);
    
    return `
        <div class="row">
            <div class="col-md-12">
                <h6>Информация о контенте</h6>
                <table class="table">
                    <tr><td><strong>Платформа:</strong></td><td class="text-center">${content.platform}</td></tr>
                    <tr><td><strong>Автор:</strong></td><td class="text-center">${content.author || 'Неизвестно'}</td></tr>
                    <tr><td><strong>Классификация:</strong></td><td class="text-center"><span class="badge ${getBadgeClass(content.classification)}">${translatedClassification}</span></td></tr>
                    <tr><td><strong>Уверенность:</strong></td><td class="text-center">${Math.round((content.confidence || 0) * 100)}%</td></tr>
                    <tr><td><strong>Дата анализа:</strong></td><td class="text-center">${new Date(content.analysis_date).toLocaleString('ru-RU')}</td></tr>
                </table>
                <h6>Контент</h6>
                <div class="border p-3 bg-light">${highlightedContent}</div>
                <h6 class="mt-3">Ключевые слова</h6>
                <div class="text-center">${Array.isArray(content.keywords) ? content.keywords.map(k => `<span class="badge bg-secondary me-1">${k}</span>`).join('') : content.keywords}</div>
                ${content.extremist_keywords && content.extremist_keywords.length > 0 ? `
                <h6 class="mt-3">Экстремистские фразы</h6>
                <div class="text-center">${content.extremist_keywords.map(k => `<span class="badge bg-warning text-dark me-1">${k}</span>`).join('')}</div>
                ` : ''}
            </div>
        </div>
    `;
}

// Функция для обрезки текста
function truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) {
        return text || '';
    }
    return text.substring(0, maxLength).trim() + '...';
}

// Функция для выделения экстремистских фраз
function highlightExtremistPhrases(text, keywords) {
    if (!text || !keywords || keywords.length === 0) {
        return text || '';
    }
    
    let highlightedText = text;
    keywords.forEach(keyword => {
        if (keyword && keyword.trim()) {
            const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            highlightedText = highlightedText.replace(regex, '<mark class="bg-warning text-dark">$1</mark>');
        }
    });
    
    return highlightedText;
}

// Функция для переключения отображения контента в результатах поиска
function toggleContent(index) {
    const shortContent = document.getElementById(`short-content-${index}`);
    const fullContent = document.getElementById(`full-content-${index}`);
    
    if (shortContent && fullContent) {
        if (shortContent.style.display === 'none') {
            shortContent.style.display = 'block';
            fullContent.style.display = 'none';
        } else {
            shortContent.style.display = 'none';
            fullContent.style.display = 'block';
        }
    }
}

// Функция для переключения отображения контента в списке контента
function toggleContentList(contentId) {
    const shortContent = document.getElementById(`short-${contentId}`);
    const fullContent = document.getElementById(`full-${contentId}`);
    
    if (shortContent && fullContent) {
        if (shortContent.style.display === 'none') {
            shortContent.style.display = 'block';
            fullContent.style.display = 'none';
        } else {
            shortContent.style.display = 'none';
            fullContent.style.display = 'block';
        }
    }
}