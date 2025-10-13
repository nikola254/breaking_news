// JavaScript для обработки форм
document.addEventListener('DOMContentLoaded', function() {
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
                resultsContent.innerHTML = formatKeywordResults(data.results);
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
                alert('Мониторинг запущен успешно!');
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
    
    // Загрузка активных сессий при загрузке страницы
    loadActiveSessions();
});

// Функция для форматирования результатов анализа аккаунта
function formatAccountResults(results) {
    let html = '<div class="row">';
    
    // Общая информация об аккаунте
    if (results.account_info) {
        html += '<div>';
        html += '<h6>Информация об аккаунте</h6>';
        html += '<div class="card">';
        html += '<div class="card-body">';
        html += `<p><strong>Платформа:</strong> ${results.account_info.platform}</p>`;
        html += `<p><strong>Имя:</strong> ${results.account_info.name || 'Неизвестно'}</p>`;
        html += `<p><strong>ID:</strong> ${results.account_info.id || 'Неизвестно'}</p>`;
        if (results.account_info.followers) {
            html += `<p><strong>Подписчики:</strong> ${results.account_info.followers}</p>`;
        }
        html += '</div></div></div>';
    }
    
    // Результаты анализа
    if (results.analysis_results) {
        html += '<div class="col-12 mt-3">';
        html += '<h6>Результаты анализа</h6>';
        
        // Общая статистика
        html += '<div class="row mb-3">';
        html += '<div class="col-md-3">';
        html += '<div class="card text-center">';
        html += '<div class="card-body">';
        html += `<h5 class="card-title text-danger">${results.analysis_results.extremist_count || 0}</h5>`;
        html += '<p class="card-text">Экстремистский контент</p>';
        html += '</div></div></div>';
        
        html += '<div class="col-md-3">';
        html += '<div class="card text-center">';
        html += '<div class="card-body">';
        html += `<h5 class="card-title text-warning">${results.analysis_results.suspicious_count || 0}</h5>`;
        html += '<p class="card-text">Подозрительный контент</p>';
        html += '</div></div></div>';
        
        html += '<div class="col-md-3">';
        html += '<div class="card text-center">';
        html += '<div class="card-body">';
        html += `<h5 class="card-title text-success">${results.analysis_results.normal_count || 0}</h5>`;
        html += '<p class="card-text">Обычный контент</p>';
        html += '</div></div></div>';
        
        html += '<div class="col-md-3">';
        html += '<div class="card text-center">';
        html += '<div class="card-body">';
        html += `<h5 class="card-title text-info">${results.analysis_results.total_analyzed || 0}</h5>`;
        html += '<p class="card-text">Всего проанализировано</p>';
        html += '</div></div></div>';
        html += '</div>';
        
        // Детальные результаты
        if (results.analysis_results.detailed_results && results.analysis_results.detailed_results.length > 0) {
            html += '<div class="table-responsive">';
            html += '<table class="table table-striped">';
            html += '<thead><tr><th style="width: 45%;">Контент</th><th style="width: 15%;">Классификация</th><th style="width: 15%;">Облачный анализ</th><th style="width: 15%;">Ключевые слова</th><th style="width: 10%;">Дата</th></tr></thead>';
            html += '<tbody>';
            
            results.analysis_results.detailed_results.forEach(item => {
                const badgeClass = item.classification === 'extremist' ? 'bg-danger' : 
                                  item.classification === 'suspicious' ? 'bg-warning' : 'bg-success';
                
                const threatColor = item.threat_color || '#6c757d';
                
                // Русская локализация классификации
                const translatedClassification = item.classification === 'extremist' ? 'экстремистский' :
                                               item.classification === 'suspicious' ? 'подозрительный' : 'обычный';
                
                // Определяем класс для цветового выделения контента
                let contentClass = '';
                if (item.classification === 'suspicious') {
                    contentClass = 'suspicious-content';
                } else if (item.classification === 'extremist') {
                    contentClass = 'extremist-content';
                } else {
                    contentClass = 'normal-content';
                }
                
                html += '<tr>';
                
                // Отображаем выделенный текст с цветовой индикацией
                const displayContent = item.highlighted_text || item.content;
                html += `<td style="border-left: 4px solid ${threatColor}; padding-left: 8px; width: 100%;">`;
                html += `<div class="${contentClass} text-break text-center" title="Нажмите для просмотра полного текста" onclick="showFullContent('${encodeURIComponent(item.content || '')}', '${item.classification}', '${Math.round((item.confidence || 0) * 100)}', '${(item.extremist_keywords || []).join(', ')}')" style="cursor: pointer;">${displayContent}</div>`;
                html += '</td>';
                
                html += `<td class="text-center"><span class="badge ${badgeClass}">${translatedClassification}</span></td>`;
                
                // Колонка с облачным анализом
                html += '<td>';
                html += `<div class="small">`;
                html += `<strong>Базовый:</strong> ${item.base_percentage || 0}%<br>`;
                html += `<strong>Итоговый:</strong> ${item.cloud_percentage || 0}%<br>`;
                html += `<strong>Метод:</strong> ${item.analysis_method || 'cloud_api'}<br>`;
                html += `<strong>Уверенность:</strong> ${((item.confidence || 0) * 100).toFixed(1)}%<br>`;
                
                if (item.social_risk_bonus && item.social_risk_bonus > 0) {
                    html += `<span class="text-info"><strong>Соц. бонус:</strong> +${item.social_risk_bonus}%</span><br>`;
                }
                
                if (item.explanation) {
                    html += `<small class="text-muted">${item.explanation}</small>`;
                }
                html += '</div>';
                html += '</td>';
                
                // Показываем ключевые слова, которые привели к классификации
                html += '<td>';
                if (item.detected_keywords && item.detected_keywords.length > 0) {
                    item.detected_keywords.forEach(keyword => {
                        html += `<span class="badge bg-secondary me-1">${keyword}</span>`;
                    });
                } else {
                    html += '<small class="text-muted">Нет</small>';
                }
                html += '</td>';
                
                html += `<td>${item.date ? new Date(item.date).toLocaleDateString() : 'Неизвестно'}</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table></div>';
        }
        
        html += '</div>';
    } else {
        // Fallback для старого формата
        html += '<div class="col-md-6">';
        html += '<h6>Общая информация</h6>';
        html += '<ul class="list-group list-group-flush">';
        html += `<li class="list-group-item">Платформа: ${results.platform}</li>`;
        html += `<li class="list-group-item">Аккаунт: ${results.account_url}</li>`;
        html += `<li class="list-group-item">Проанализировано постов: ${results.posts_analyzed}</li>`;
        html += `<li class="list-group-item">Дата анализа: ${new Date(results.analysis_date).toLocaleString()}</li>`;
        html += '</ul></div>';
        
        // Результаты классификации
        html += '<div class="col-md-6">';
        html += '<h6>Результаты классификации</h6>';
        html += '<ul class="list-group list-group-flush">';
        html += `<li class="list-group-item">Экстремистский контент: <span class="badge bg-danger">${results.extremist_content_count || 0}</span></li>`;
        html += `<li class="list-group-item">Подозрительный контент: <span class="badge bg-warning">${results.suspicious_content_count || 0}</span></li>`;
        html += `<li class="list-group-item">Обычный контент: <span class="badge bg-success">${results.normal_content_count || 0}</span></li>`;
        html += '</ul></div>';
        
        html += '</div>';
        
        // Подробные результаты
        if (results.detailed_results && results.detailed_results.length > 0) {
            html += '<div class="mt-3">';
            html += '<h6>Подробные результаты</h6>';
            html += '<div class="table-responsive">';
            html += '<table class="table table-striped">';
            html += '<thead><tr><th style="width: 60%;">Пост</th><th style="width: 15%;">Классификация</th><th style="width: 15%;">Уверенность</th><th style="width: 10%;">Дата</th></tr></thead>';
            html += '<tbody>';
            
            results.detailed_results.forEach(result => {
                const badgeClass = result.classification === 'extremist' ? 'bg-danger' : 
                                  result.classification === 'suspicious' ? 'bg-warning' : 'bg-success';
                
                // Определяем цвет угрозы
                const threatColor = result.threat_color || '#6c757d';
                
                html += '<tr>';
                
                // Отображаем выделенный текст или обычный контент полностью
                const displayContent = result.highlighted_text || result.content;
                html += `<td style="border-left: 4px solid ${threatColor}; padding-left: 8px;">${displayContent}</td>`;
                
                html += `<td><span class="badge ${badgeClass}">${result.classification}</span></td>`;
                html += `<td>${(result.confidence * 100).toFixed(1)}%</td>`;
                html += `<td>${new Date(result.date).toLocaleDateString()}</td>`;
                html += '</tr>';
            });
            
            html += '</tbody></table></div></div>';
        }
    }
    
    return html;
}

// Функция для форматирования результатов поиска по ключевым словам
function formatKeywordResults(results) {
    let html = '<div class="row">';
    
    // Общая статистика
    html += '<div>';
    html += '<h6>Результаты поиска</h6>';
    html += `<p>Найдено результатов: <strong>${results.total_found || 0}</strong></p>`;
    
    // Статистика анализа
    if (results.analysis_summary) {
        html += '<div class="mb-3">';
        html += '<h6>Анализ контента</h6>';
        html += '<div class="d-flex gap-2">';
        html += `<span class="badge bg-danger">Экстремистский: ${results.analysis_summary.extremist_count || 0}</span>`;
        html += `<span class="badge bg-warning">Подозрительный: ${results.analysis_summary.suspicious_count || 0}</span>`;
        html += `<span class="badge bg-success">Обычный: ${results.analysis_summary.normal_count || 0}</span>`;
        html += '</div></div>';
    }
    
    html += '</div>';
    
    // Результаты по платформам
    if (results.platform_results) {
        Object.keys(results.platform_results).forEach(platform => {
            const platformResults = results.platform_results[platform];
            html += '<div class="col-12 mb-4">';
            html += `<div class="card"><div class="card-header d-flex justify-content-between align-items-center">`;
            html += `<span>${platform.toUpperCase()}</span>`;
            html += `<span class="badge bg-primary">${platformResults.count || 0} результатов</span>`;
            html += '</div>';
            html += '<div class="card-body">';
            
            if (platformResults.error) {
                html += `<div class="alert alert-warning">${platformResults.error}</div>`;
            } else if (platformResults.items && platformResults.items.length > 0) {
                html += '<div class="table-responsive">';
                html += '<table class="table table-sm">';
                html += '<thead><tr><th style="width: 45%;">Контент</th><th style="width: 15%;">Классификация</th><th style="width: 15%;">Уверенность</th><th style="width: 15%;">Источник</th><th style="width: 10%;">Дата</th></tr></thead>';
                html += '<tbody>';
                
                platformResults.items.forEach(item => {
                    const badgeClass = item.classification === 'extremist' ? 'bg-danger' : 
                                      item.classification === 'suspicious' ? 'bg-warning' : 'bg-success';
                    
                    const threatColor = item.threat_color || '#6c757d';
                    
                    html += '<tr>';
                    
                    // Отображаем выделенный текст
                    const displayContent = item.highlighted_text || item.content;
                    const shortContent = displayContent.length > 200 ? displayContent.substring(0, 200) + '...' : displayContent;
                    html += `<td style="border-left: 4px solid ${threatColor}; padding-left: 8px; width: 100%;">`;
                    html += `<div title="${item.content}">${shortContent}</div>`;
                    html += '</td>';
                    
                    html += `<td class="text-center"><span class="badge ${badgeClass}">${item.classification}</span></td>`;
                    html += `<td class="text-center">${(item.confidence * 100).toFixed(1)}%</td>`;
                    
                    // Источник (канал или URL)
                    const source = item.channel || item.url || 'Неизвестно';
                    html += `<td class="text-center"><small>${source}</small></td>`;
                    
                    // Дата
                    const date = item.date ? new Date(item.date).toLocaleDateString() : 'Неизвестно';
                    html += `<td class="text-center"><small>${date}</small></td>`;
                    
                    html += '</tr>';
                });
                
                html += '</tbody></table></div>';
            } else {
                html += '<p class="text-muted">Результатов не найдено</p>';
            }
            
            html += '</div></div></div>';
        });
    }
    
    html += '</div>';
    return html;
}

// Функция для загрузки активных сессий мониторинга
function loadActiveSessions() {
    fetch('/social-analysis/active-sessions')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('activeSessions');
            if (data.success && data.sessions.length > 0) {
                let html = '<div class="table-responsive">';
                html += '<table class="table table-striped">';
                html += '<thead><tr><th>Название</th><th>Статус</th><th>Платформы</th><th>Ключевые слова</th><th>Найдено</th><th>Статистика</th><th>Интервал</th><th>Действия</th></tr></thead>';
                html += '<tbody>';
                
                data.sessions.forEach(session => {
                    html += '<tr>';
                    html += `<td>${session.session_name}</td>`;
                    html += `<td><span class="badge ${session.is_active ? 'bg-success' : 'bg-secondary'}">${session.is_active ? 'Активен' : 'Остановлен'}</span></td>`;
                    
                    // Платформы
                    const platforms = session.platforms || [];
                    html += `<td>${platforms.length > 0 ? platforms.join(', ') : 'Не указаны'}</td>`;
                    
                    // Ключевые слова (отображаем полностью)
                    const keywords = session.keywords || 'Не указаны';
                    html += `<td title="${keywords}">${keywords}</td>`;
                    
                    // Общее количество найденного
                    html += `<td><span class="badge bg-info">${session.found_count || 0}</span></td>`;
                    
                    // Статистика по типам контента
                    html += '<td>';
                    if (session.extremist_count > 0) {
                        html += `<span class="badge bg-danger me-1" title="Экстремистский контент">${session.extremist_count}</span>`;
                    }
                    if (session.suspicious_count > 0) {
                        html += `<span class="badge bg-warning me-1" title="Подозрительный контент">${session.suspicious_count}</span>`;
                    }
                    if (session.normal_count > 0) {
                        html += `<span class="badge bg-success me-1" title="Обычный контент">${session.normal_count}</span>`;
                    }
                    if (!session.extremist_count && !session.suspicious_count && !session.normal_count) {
                        html += '<span class="text-muted">-</span>';
                    }
                    html += '</td>';
                    
                    html += `<td>${session.check_interval} мин</td>`;
                    
                    // Действия
                    html += '<td>';
                    if (session.is_active && session.id !== 'example') {
                        html += `<button class="btn btn-sm btn-danger" onclick="stopSession('${session.id}')">Остановить</button>`;
                    } else if (session.id === 'example') {
                        html += '<span class="text-muted">-</span>';
                    } else {
                        html += '<span class="text-muted">Остановлен</span>';
                    }
                    html += '</td>';
                    
                    html += '</tr>';
                });
                
                html += '</tbody></table></div>';
                container.innerHTML = html;
            } else {
                container.innerHTML = '<p class="text-muted">Нет активных сессий мониторинга</p>';
            }
        })
        .catch(error => {
            console.error('Error loading sessions:', error);
            document.getElementById('activeSessions').innerHTML = '<p class="text-danger">Ошибка загрузки сессий</p>';
        });
}

// Функция для остановки сессии мониторинга
function stopSession(sessionId) {
    if (confirm('Вы уверены, что хотите остановить эту сессию мониторинга?')) {
        fetch(`/social-analysis/stop-session/${sessionId}`, {
            method: 'POST'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Сессия остановлена');
                loadActiveSessions();
            } else {
                alert('Ошибка: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Произошла ошибка при остановке сессии');
        });
    }
}

// Функция для выделения подозрительных слов в тексте
function highlightSuspiciousWords(text, keywords, classification) {
    if (!keywords || !keywords.trim()) {
        return text;
    }
    
    let highlightedText = text;
    
    // Разбираем ключевые слова (могут быть разделены запятыми или пробелами)
    const keywordList = keywords.split(/[,\s]+/).map(k => k.trim()).filter(k => k.length > 2);
    
    // Определяем CSS класс в зависимости от классификации
    const cssClass = classification === 'extremist' ? 'threat-keyword' : 
                     classification === 'suspicious' ? 'hate-keyword' : 'extremist-keyword';
    
    // Сортируем ключевые слова по длине (сначала длинные, чтобы избежать частичных замен)
    keywordList.sort((a, b) => b.length - a.length);
    
    keywordList.forEach(keyword => {
        if (keyword.length > 2) {
            // Экранируем специальные символы регулярных выражений
            const escapedKeyword = keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            
            // Создаем регулярное выражение для поиска слова (с границами слов)
            const regex = new RegExp(`\\b${escapedKeyword}\\b`, 'gi');
            
            // Заменяем найденные слова на выделенные версии
            highlightedText = highlightedText.replace(regex, (match) => {
                // Проверяем, не находится ли слово уже внутри тега span
                const beforeMatch = highlightedText.substring(0, highlightedText.indexOf(match));
                const openSpans = (beforeMatch.match(/<span[^>]*>/g) || []).length;
                const closeSpans = (beforeMatch.match(/<\/span>/g) || []).length;
                
                // Если количество открывающих и закрывающих тегов не равно, значит мы внутри span
                if (openSpans !== closeSpans) {
                    return match;
                }
                
                return `<span class="${cssClass}" title="Подозрительное слово: ${keyword}">${match}</span>`;
            });
        }
    });
    
    return highlightedText;
}

// Функция для показа полного контента
function showFullContent(encodedContent, classification, confidence, keywords) {
    // Декодируем контент
    let content = '';
    try {
        content = decodeURIComponent(encodedContent);
    } catch (e) {
        content = encodedContent; // Если декодирование не удалось, используем как есть
    }
    
    // Выделяем подозрительные слова в тексте
    const highlightedContent = highlightSuspiciousWords(content, keywords, classification);
    
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.id = 'fullContentModal';
    modal.tabIndex = -1;
    modal.setAttribute('aria-labelledby', 'fullContentModalLabel');
    modal.setAttribute('aria-hidden', 'true');
    
    // Определяем русскую локализацию
    const translatedClassification = classification === 'normal' ? 'обычный' : 
                                   classification === 'suspicious' ? 'подозрительный' : 
                                   classification === 'extremist' ? 'экстремистский' : classification;
    
    // Определяем класс для цветового выделения фона
    const contentClass = classification === 'suspicious' ? 'suspicious-content' : 
                        classification === 'extremist' ? 'extremist-content' : 'normal-content';
    
    // Определяем цвет бейджа
    const badgeColor = classification === 'normal' ? 'success' : 
                      classification === 'suspicious' ? 'warning' : 'danger';
    
    modal.innerHTML = `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="fullContentModalLabel">Полный текст поста</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body" style="max-height: 75vh; overflow-y: auto; padding: 0;">
                    <div class="${contentClass}" style="margin: 0; border-radius: 0;">
                        <div class="content-text-center" style="padding: 20px;">
                            <div style="color: #000; text-align: left; font-size: 16px; line-height: 1.6; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; background-color: #fff; padding: 10px; border-radius: 4px;">
                                ${highlightedContent.replace(/\s+/g, ' ').trim()}
                            </div>
                        </div>
                        <div class="classification-center">
                            <span class="badge bg-${badgeColor} me-2" style="font-size: 14px; padding: 8px 12px;">
                                ${translatedClassification}
                            </span>
                            <span class="badge bg-secondary" style="font-size: 14px; padding: 8px 12px;">${confidence}%</span>
                            ${keywords && keywords.trim() ? `<div class="mt-3"><small class="text-muted"><strong>Ключевые слова:</strong> ${keywords}</small></div>` : ''}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Закрыть</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    const modalInstance = new bootstrap.Modal(modal);
    modalInstance.show();
    
    // Удаляем модальное окно после закрытия
    modal.addEventListener('hidden.bs.modal', function () {
        document.body.removeChild(modal);
    });
}