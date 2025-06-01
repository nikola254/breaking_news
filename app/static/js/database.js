// Глобальные переменные
let currentSource = 'telegram';
let currentPage = 1;
let currentFilter = null;
let currentFilterValue = null;
let currentDays = 7;
let totalPages = 1;
let currentSearchQuery = '';

// Переменные для управления парсингом
let activeParsers = [];
let isParsingActive = false;
let logWindowVisible = false;

// DOM-элементы
const dataTable = document.getElementById('data-table');
const tableHeader = document.getElementById('table-header');
const tableBody = document.getElementById('table-body');
const pagination = document.getElementById('pagination');
const loading = document.getElementById('loading');
const errorContainer = document.getElementById('error-container');
const filterContainer = document.getElementById('filter-container');
const daysSelect = document.getElementById('days-select');
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Обработчики событий для кнопок выбора источника данных
    document.querySelectorAll('.db-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.db-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSource = btn.dataset.source;
            currentPage = 1;
            currentFilter = null;
            currentFilterValue = null;
            loadData();
        });
    });
    
    // Обработчик изменения периода
    daysSelect.addEventListener('change', () => {
        currentDays = parseInt(daysSelect.value);
        currentPage = 1;
        loadData();
    });
    
    // Обработчик для поиска
    searchBtn.addEventListener('click', () => {
        currentSearchQuery = searchInput.value.trim();
        currentPage = 1;
        loadData();
    });
    
    // Обработчик для поиска по нажатию Enter
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentSearchQuery = searchInput.value.trim();
            currentPage = 1;
            loadData();
        }
    });
    
    // Обработчики для кнопок в навигации
    const parseBtn = document.getElementById('parse-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    
    if (parseBtn) {
        parseBtn.addEventListener('click', () => {
            if (confirm('Вы уверены, что хотите запустить процесс парсинга? Это может занять некоторое время.')) {
                openParserSelectionModal();
            }
        });
    }
    
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadData();
        });
    }
    
    // Загрузка данных при первом открытии страницы
    loadData();
    
    // Инициализируем WebSocket и проверяем статус парсеров
    initWebSocket();
    
    // Восстанавливаем состояние окна логирования если оно было открыто
    restoreLogWindowState();
});

// Сохраняем состояние окна логирования при переходе на другую страницу
window.addEventListener('beforeunload', function() {
    // Сохраняем состояние в sessionStorage
    sessionStorage.setItem('logWindowVisible', logWindowVisible);
    if (logWindowVisible) {
        const logContent = document.getElementById('log-content');
        if (logContent) {
            sessionStorage.setItem('logContent', logContent.innerHTML);
        }
    }
});



// Функция загрузки данных из API
function loadData() {
    showLoading(true);
    clearError();
    
    console.log('Загрузка данных для страницы:', currentPage);
    
    // Вычисляем offset на основе текущей страницы и лимита
    const limit = 20;
    const offset = (currentPage - 1) * limit;
    
    // Формирование URL запроса с параметрами
    let url = `/api/news?source=${currentSource}&limit=${limit}&offset=${offset}`;
    
    // Добавляем фильтр по дням
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - currentDays);
    
    // Добавляем фильтры если они установлены
    if (currentFilter && currentFilterValue) {
        url += `&${currentFilter}=${encodeURIComponent(currentFilterValue)}`;
    }
    
    // Добавляем поисковый запрос если он есть
    if (currentSearchQuery) {
        url += `&search=${encodeURIComponent(currentSearchQuery)}`;
    }
    
    console.log('URL запроса:', url);
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                console.log('Получены данные:', data);
                console.log('Текущая страница:', data.current_page);
                console.log('Всего страниц:', data.total_pages);
                
                // Обновляем данные на странице
                updateTable(data.data);
                updatePagination(data.total_pages, data.current_page);
                updateFilters(data);
                totalPages = data.total_pages;
                currentPage = data.current_page; // Синхронизируем текущую страницу с ответом сервера
            } else {
                showError(data.message || 'Ошибка при загрузке данных');
            }
        })
        .catch(error => {
            showError(`Ошибка при загрузке данных: ${error.message}`);
        })
        .finally(() => {
            showLoading(false);
        });
}

// Функция обновления таблицы с данными
function updateTable(data) {
    // Очистка таблицы
    tableHeader.innerHTML = '';
    tableBody.innerHTML = '';
    
    if (data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="5" style="text-align: center;">Нет данных для отображения</td></tr>';
        return;
    }
    
    // Создание заголовков таблицы в зависимости от источника
    const headers = getHeadersForSource(currentSource);
    headers.forEach(header => {
        const th = document.createElement('th');
        th.textContent = header.label;
        if (header.class) th.className = header.class;
        tableHeader.appendChild(th);
    });
    
    // Заполнение таблицы данными
    data.forEach(item => {
        const row = document.createElement('tr');
        
        headers.forEach(header => {
            const cell = document.createElement('td');
            
            if (header.key === 'parsed_date' || header.key === 'date') {
                // Форматируем дату
                const dateValue = item['parsed_date'] || item['date'];
                if (dateValue) {
                    try {
                        const date = new Date(dateValue);
                        if (!isNaN(date.getTime())) {
                            cell.textContent = date.toLocaleString('ru-RU');
                        } else {
                            cell.textContent = dateValue;
                        }
                    } catch (e) {
                        cell.textContent = dateValue;
                    }
                } else {
                    cell.textContent = '-';
                }
                cell.className = 'date-col';
            } else if (header.key === 'title') {
                // Для заголовка добавляем возможность открытия модального окна
                cell.className = 'title-col';
                cell.textContent = item['title'] || '-';
                cell.style.cursor = 'pointer';
                cell.title = 'Нажмите, чтобы открыть полную статью';
                
                // Добавляем обработчик клика для открытия модального окна
                cell.addEventListener('click', () => {
                    openArticleModal(item);
                });
            } else if (header.key === 'content') {
                // Для контента добавляем возможность разворачивания
                cell.className = 'content-cell';
                const content = item['content'] || '-';
                
                // Ограничиваем длину контента в таблице
                const shortContent = content.length > 100 ? content.substring(0, 100) + '...' : content;
                cell.textContent = shortContent;
                
                if (content && content.length > 100) {
                    const expandBtn = document.createElement('button');
                    expandBtn.className = 'expand-btn';
                    expandBtn.textContent = '[Развернуть]';
                    expandBtn.addEventListener('click', () => {
                        if (cell.classList.contains('expanded')) {
                            cell.textContent = shortContent;
                            cell.classList.remove('expanded');
                            cell.appendChild(expandBtn);
                            expandBtn.textContent = '[Развернуть]';
                        } else {
                            cell.textContent = content;
                            cell.classList.add('expanded');
                            cell.appendChild(expandBtn);
                            expandBtn.textContent = '[Свернуть]';
                        }
                    });
                    cell.appendChild(expandBtn);
                }
            } else if (header.key === 'category') {
                // Для категории переводим на русский язык
                const categoryTranslations = {
                    'ukraine': 'Украина',
                    'middle_east': 'Ближний восток',
                    'fake_news': 'Фейки',
                    'info_war': 'Инфовойна',
                    'europe': 'Европа',
                    'usa': 'США',
                    'other': 'Другое'
                };
                const category = item['category'] || 'other';
                cell.textContent = categoryTranslations[category] || category;
                cell.className = 'category-col';
            } else {
                // Для остальных полей просто выводим значение
                cell.textContent = item[header.key] || '-';
            }
            
            row.appendChild(cell);
        });
        
        tableBody.appendChild(row);
    });
}

// Функция получения заголовков таблицы в зависимости от источника
function getHeadersForSource(source) {
    // Унифицированная структура для всех источников
    return [
        { key: 'parsed_date', label: 'Дата', class: 'date-col' },
        { key: 'title', label: 'Заголовок', class: 'title-col' },
        { key: 'category', label: 'Категория', class: 'category-col' }
    ];
}

// Функция обновления пагинации
function updatePagination(totalPages, currentPage) {
    console.log('Обновление пагинации:', totalPages, currentPage);
    pagination.innerHTML = '';
    
    if (totalPages <= 1) {
        console.log('Всего одна страница, пагинация не нужна');
        return;
    }
    
    // Кнопка "Предыдущая"
    if (currentPage > 1) {
        addPageButton('«', currentPage - 1);
    }
    
    // Номера страниц
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    console.log('Диапазон страниц:', startPage, endPage);
    
    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === parseInt(currentPage);
        console.log('Добавление кнопки страницы:', i, 'активна:', isActive);
        addPageButton(i, i, isActive);
    }
    
    // Кнопка "Следующая"
    if (currentPage < totalPages) {
        addPageButton('»', currentPage + 1);
    }
}

// Функция добавления кнопки пагинации
function addPageButton(text, page, isActive = false) {
    const button = document.createElement('button');
    button.className = `page-btn${isActive ? ' active' : ''}`;
    button.textContent = text;
    button.addEventListener('click', function() {
        console.log('Нажата кнопка пагинации:', page);
        if (page !== currentPage) {
            currentPage = page;
            console.log('Установлена новая страница:', currentPage);
            loadData();
        }
    });
    pagination.appendChild(button);
}

// Функция обновления фильтров
function updateFilters(data) {
    filterContainer.innerHTML = '';
    
    let filterOptions = [];
    let filterName = '';
    
    // Определяем доступные фильтры в зависимости от источника
    if (currentSource === 'telegram' && data.available_channels) {
        filterOptions = data.available_channels;
        filterName = 'telegram_channel';
        createFilterSelect('Канал:', filterName, filterOptions);
    } else if ((currentSource === 'israil' || currentSource === 'ria') && data.available_categories) {
        filterOptions = data.available_categories;
        filterName = 'category';
        createFilterSelect('Категория:', filterName, filterOptions);
    }
}

// Функция создания выпадающего списка для фильтрации
function createFilterSelect(label, filterName, options) {
    const container = document.createElement('div');
    container.style.display = 'flex';
    container.style.alignItems = 'center';
    container.style.gap = '10px';
    
    const labelElement = document.createElement('label');
    labelElement.textContent = label;
    container.appendChild(labelElement);
    
    const select = document.createElement('select');
    select.className = 'filter-select';
    
    // Добавляем опцию "Все"
    const allOption = document.createElement('option');
    allOption.value = '';
    allOption.textContent = 'Все';
    select.appendChild(allOption);
    
    // Добавляем остальные опции
    options.forEach(option => {
        const optionElement = document.createElement('option');
        optionElement.value = option;
        optionElement.textContent = option;
        if (currentFilter === filterName && currentFilterValue === option) {
            optionElement.selected = true;
        }
        select.appendChild(optionElement);
    });
    
    // Обработчик изменения фильтра
    select.addEventListener('change', () => {
        currentFilter = select.value ? filterName : null;
        currentFilterValue = select.value;
        currentPage = 1;
        loadData();
    });
    
    container.appendChild(select);
    filterContainer.appendChild(container);
}

// Функция отображения/скрытия индикатора загрузки
function showLoading(show) {
    loading.style.display = show ? 'block' : 'none';
    dataTable.style.display = show ? 'none' : 'table';
}

// Функция отображения ошибки
function showError(message) {
    errorContainer.innerHTML = `<div class="error-message">${message}</div>`;
}

// Функция очистки ошибки
function clearError() {
    errorContainer.innerHTML = '';
}

// Функция открытия модального окна со статьей
function openArticleModal(article) {
    const modal = document.getElementById('article-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalContent = document.getElementById('modal-content');
    const modalSource = document.getElementById('modal-source');
    const modalDate = document.getElementById('modal-date');
    const modalLink = document.getElementById('modal-link');
    
    // Заполняем данными модальное окно
    modalTitle.textContent = article.title || 'Без заголовка';
    modalContent.textContent = article.content || 'Содержание отсутствует';
    
    // Устанавливаем метаданные
    modalSource.textContent = article.source || 'Неизвестный источник';
    
    const dateValue = article.parsed_date || article.date;
    if (dateValue) {
        try {
            const date = new Date(dateValue);
            if (!isNaN(date.getTime())) {
                modalDate.textContent = date.toLocaleString('ru-RU');
            } else {
                modalDate.textContent = dateValue;
            }
        } catch (e) {
            modalDate.textContent = dateValue;
        }
    } else {
        modalDate.textContent = 'Дата неизвестна';
    }
    
    // Устанавливаем ссылку на оригинал
    // Проверяем различные возможные поля для ссылки
    const linkValue = article.link || article.telegram_link || article.israil_link || article.url || article.original_url;
    
    if (linkValue && linkValue.trim() !== '') {
        modalLink.href = linkValue;
        modalLink.style.display = 'inline';
        modalLink.target = '_blank'; // Убеждаемся, что ссылка открывается в новой вкладке
    } else {
        modalLink.style.display = 'none';
    }
    
    // Отображаем модальное окно
    modal.classList.add('show');
    modal.style.display = 'block';
    
    // Обработчик закрытия модального окна
    const closeBtn = modal.querySelector('.article-close-btn');
    closeBtn.onclick = function() {
        modal.classList.remove('show');
        modal.style.display = 'none';
    }
    
    // Закрытие при клике вне модального окна
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.classList.remove('show');
            modal.style.display = 'none';
        }
    }
}

// Функция открытия модального окна выбора парсеров
function openParserSelectionModal() {
    const modal = document.getElementById('parser-modal');
    modal.style.display = 'block';
    
    // Обработчик закрытия модального окна
    const closeBtn = modal.querySelector('.close-modal');
    closeBtn.onclick = function() {
        modal.style.display = 'none';
    }
    
    // Закрытие при клике вне модального окна
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    }
    
    // Обработчик кнопки запуска парсинга
    const startBtn = document.getElementById('start-parsing-btn');
    startBtn.onclick = function() {
        const selectedParsers = [];
        const checkboxes = modal.querySelectorAll('input[name="parser"]:checked');
        checkboxes.forEach(checkbox => {
            selectedParsers.push(checkbox.value);
        });
        
        if (selectedParsers.length > 0) {
            modal.style.display = 'none';
            runParsers(selectedParsers);
        } else {
            alert('Выберите хотя бы один источник для парсинга!');
        }
    }
}

// Функции для работы с окном логирования
function showParserLog() {
    const logWindow = document.getElementById('parser-log');
    logWindow.style.display = 'block';
    logWindowVisible = true;
    
    // Закрытие окна логирования
    const closeBtn = logWindow.querySelector('.log-close');
    closeBtn.onclick = function() {
        logWindow.style.display = 'none';
        logWindowVisible = false;
    };
    
    // Обработчик кнопки остановки парсинга
    const stopBtn = document.getElementById('stop-parsing-btn');
    stopBtn.onclick = function() {
        stopParsing();
    };
    
    // Обновляем состояние кнопки остановки
    updateStopButtonState();
}

function addLogEntry(message, type = 'info') {
    const logContent = document.getElementById('log-content');
    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    logContent.appendChild(entry);
    logContent.scrollTop = logContent.scrollHeight;
}

function clearLog() {
    const logContent = document.getElementById('log-content');
    logContent.innerHTML = '';
}

// Функция для остановки парсинга
function stopParsing() {
    if (!isParsingActive) {
        addLogEntry('Нет активных процессов парсинга для остановки', 'info');
        return;
    }
    
    addLogEntry('Отправка команды остановки парсинга...', 'info');
    
    fetch('/api/stop_parser', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sources: ['all'] })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Остановка парсинга:', data);
        addLogEntry(data.message, data.status === 'success' ? 'success' : 'info');
        if (data.status === 'success') {
            isParsingActive = false;
            activeParsers = [];
            updateStopButtonState();
        }
    })
    .catch(error => {
        console.error('Ошибка при остановке парсинга:', error);
        addLogEntry(`Ошибка при остановке парсинга: ${error.message}`, 'error');
    });
}

// Функция для обновления состояния кнопки остановки
function updateStopButtonState() {
    const stopBtn = document.getElementById('stop-parsing-btn');
    if (stopBtn) {
        stopBtn.disabled = !isParsingActive;
        stopBtn.title = isParsingActive ? 'Остановить парсинг' : 'Нет активных процессов';
    }
}

// Функция для проверки статуса активных парсеров
function checkParserStatus() {
    fetch('/api/parser_status')
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            activeParsers = data.active_parsers;
            isParsingActive = activeParsers.length > 0;
            updateStopButtonState();
        }
    })
    .catch(error => {
        console.error('Ошибка при проверке статуса парсеров:', error);
    });
}

// Функция для восстановления состояния окна логирования
function restoreLogWindowState() {
    const savedLogWindowVisible = sessionStorage.getItem('logWindowVisible');
    const savedLogContent = sessionStorage.getItem('logContent');
    
    if (savedLogWindowVisible === 'true') {
        logWindowVisible = true;
        showParserLog();
        
        if (savedLogContent) {
            const logContent = document.getElementById('log-content');
            if (logContent) {
                logContent.innerHTML = savedLogContent;
                logContent.scrollTop = logContent.scrollHeight;
            }
        }
    }
}

// Инициализация WebSocket соединения
let socket = null;

function initWebSocket() {
    if (!socket) {
        socket = io();
        
        // Обработчик получения логов от парсера
        socket.on('parser_log', function(data) {
            addLogEntry(data.message, data.type);
            
            // Обновляем статус парсинга на основе сообщений
            if (data.message.includes('Запуск парсера')) {
                isParsingActive = true;
                if (!activeParsers.includes(data.source)) {
                    activeParsers.push(data.source);
                }
                updateStopButtonState();
            } else if (data.message.includes('завершен') || data.message.includes('остановлен')) {
                activeParsers = activeParsers.filter(parser => parser !== data.source);
                isParsingActive = activeParsers.length > 0;
                updateStopButtonState();
            }
        });
        
        socket.on('connect', function() {
            console.log('WebSocket соединение установлено');
            // Проверяем статус парсеров при подключении
            checkParserStatus();
        });
        
        socket.on('disconnect', function() {
            console.log('WebSocket соединение разорвано');
        });
    }
}

// Функция для запуска парсеров
function runParsers(sources) {
    // Инициализируем WebSocket если еще не инициализирован
    initWebSocket();
    
    // Показываем окно логирования и очищаем предыдущие логи
    showParserLog();
    clearLog();
    addLogEntry('Инициализация парсинга...', 'info');
    addLogEntry(`Выбранные источники: ${sources.join(', ')}`, 'info');
    
    // Обновляем состояние парсинга
    isParsingActive = true;
    activeParsers = [...sources];
    updateStopButtonState();
    
    fetch('/api/run_parser', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sources: sources })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Парсинг запущен:', data);
        addLogEntry('Запрос на парсинг отправлен', 'success');
    })
    .catch(error => {
        console.error('Ошибка при запуске парсинга:', error);
        addLogEntry(`Ошибка при запуске парсинга: ${error.message}`, 'error');
        isParsingActive = false;
        activeParsers = [];
        updateStopButtonState();
    });
}