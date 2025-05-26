// Глобальные переменные
let currentSource = 'telegram';
let currentPage = 1;
let currentFilter = null;
let currentFilterValue = null;
let currentDays = 7;
let totalPages = 1;

// DOM-элементы
const dataTable = document.getElementById('data-table');
const tableHeader = document.getElementById('table-header');
const tableBody = document.getElementById('table-body');
const pagination = document.getElementById('pagination');
const loading = document.getElementById('loading');
const errorContainer = document.getElementById('error-container');
const filterContainer = document.getElementById('filter-container');
const daysSelect = document.getElementById('days-select');

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
});

// Функция загрузки данных из API
function loadData() {
    showLoading(true);
    clearError();
    
    // Формирование URL запроса с параметрами
    let url = `/api/news?source=${currentSource}&page=${currentPage}&limit=20`;
    
    // Добавляем фильтр по дням
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - currentDays);
    
    // Добавляем фильтры если они установлены
    if (currentFilter && currentFilterValue) {
        url += `&${currentFilter}=${encodeURIComponent(currentFilterValue)}`;
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Обновляем данные на странице
                updateTable(data.data);
                updatePagination(data.total_pages, data.current_page);
                updateFilters(data);
                totalPages = data.total_pages;
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
            
            if (header.key === 'link' || header.key === 'telegram_link' || header.key === 'israil_link') {
                // Для ссылок создаем элемент <a>
                cell.className = 'link-cell';
                const linkValue = item[header.key] || item.link || item.telegram_link || item.israil_link;
                if (linkValue) {
                    const link = document.createElement('a');
                    link.href = linkValue;
                    link.target = '_blank';
                    link.textContent = 'Открыть';
                    cell.appendChild(link);
                } else {
                    cell.textContent = '-';
                }
            } else if (header.key === 'content') {
                // Для контента добавляем возможность разворачивания
                cell.className = 'content-cell';
                const content = item[header.key] || '-';
                cell.textContent = content;
                
                if (content && content.length > 100) {
                    const expandBtn = document.createElement('button');
                    expandBtn.className = 'expand-btn';
                    expandBtn.textContent = '[Развернуть]';
                    expandBtn.addEventListener('click', () => {
                        cell.classList.toggle('expanded');
                        expandBtn.textContent = cell.classList.contains('expanded') ? '[Свернуть]' : '[Развернуть]';
                    });
                    cell.appendChild(expandBtn);
                }
            } else if (header.key === 'title') {
                // Для заголовка добавляем возможность открытия модального окна
                cell.className = 'title-col';
                cell.textContent = item[header.key] || '-';
                cell.style.cursor = 'pointer';
                cell.title = 'Нажмите, чтобы открыть полную статью';
                
                // Добавляем обработчик клика для открытия модального окна
                cell.addEventListener('click', () => {
                    openArticleModal(item);
                });
            } else if (header.key === 'parsed_date' || header.key === 'date') {
                // Форматируем дату
                const dateValue = item[header.key] || item.parsed_date || item.date;
                if (dateValue) {
                    const date = new Date(dateValue);
                    cell.textContent = date.toLocaleString('ru-RU');
                } else {
                    cell.textContent = '-';
                }
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
    switch (source) {
        case 'telegram':
            return [
                { key: 'parsed_date', label: 'Дата', class: 'date-col' },
                { key: 'telegram_channel', label: 'Канал', class: 'source-col' },
                { key: 'title', label: 'Заголовок', class: 'title-col' },
                { key: 'content', label: 'Содержание' },
                { key: 'telegram_link', label: 'Ссылка' }
            ];
        case 'israil':
            return [
                { key: 'parsed_date', label: 'Дата', class: 'date-col' },
                { key: 'source', label: 'Источник', class: 'source-col' },
                { key: 'category', label: 'Категория' },
                { key: 'title', label: 'Заголовок', class: 'title-col' },
                { key: 'content', label: 'Содержание' },
                { key: 'israil_link', label: 'Ссылка' }
            ];
        case 'ria':
            return [
                { key: 'parsed_date', label: 'Дата', class: 'date-col' },
                { key: 'source', label: 'Источник', class: 'source-col' },
                { key: 'category', label: 'Категория' },
                { key: 'title', label: 'Заголовок', class: 'title-col' },
                { key: 'content', label: 'Содержание' },
                { key: 'link', label: 'Ссылка' }
            ];
        default:
            return [];
    }
}

// Функция обновления пагинации
function updatePagination(totalPages, currentPage) {
    pagination.innerHTML = '';
    
    if (totalPages <= 1) return;
    
    // Кнопка "Предыдущая"
    if (currentPage > 1) {
        addPageButton('«', currentPage - 1);
    }
    
    // Номера страниц
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        addPageButton(i, i, i === currentPage);
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
    button.addEventListener('click', () => {
        if (page !== currentPage) {
            currentPage = page;
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
    if (currentSource === 'telegram') {
        modalSource.textContent = article.telegram_channel || 'Неизвестный канал';
    } else {
        modalSource.textContent = article.source || 'Неизвестный источник';
    }
    
    const dateValue = article.parsed_date || article.date;
    if (dateValue) {
        const date = new Date(dateValue);
        modalDate.textContent = date.toLocaleString('ru-RU');
    } else {
        modalDate.textContent = 'Дата неизвестна';
    }
    
    // Устанавливаем ссылку на оригинал
    const linkValue = article.link || article.telegram_link || article.israil_link;
    if (linkValue) {
        modalLink.href = linkValue;
        modalLink.style.display = 'inline';
    } else {
        modalLink.style.display = 'none';
    }
    
    // Отображаем модальное окно
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
}

// Функция для запуска парсеров
function runParsers(sources) {
    showLoading(true);
    
    // Отправляем запрос на запуск парсинга
    fetch('/api/run_parser', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ source: sources.length === 3 ? 'all' : sources.join(',') })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Парсинг успешно запущен! Обновите данные через несколько минут.');
            // Автоматически обновляем данные через 5 секунд
            setTimeout(() => {
                loadData();
            }, 5000);
        } else {
            showError(data.message || 'Ошибка при запуске парсинга');
        }
    })
    .catch(error => {
        showError(`Ошибка при запуске парсинга: ${error.message}`);
    })
    .finally(() => {
        showLoading(false);
    });
}