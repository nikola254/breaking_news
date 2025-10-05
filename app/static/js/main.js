// Основной JavaScript файл для приложения NewsAnalytics

// Глобальные переменные
let currentCategory = 'military_operations';
let currentPage = 1;
let availableCategories = [];



// Функция для загрузки новостей
function loadNews(category, page) {
    const validCategory = category;
    const limit = 10;
    const offset = (page - 1) * limit;

    // Для категории 'all' используем source=all без параметра category
    const url = validCategory === 'all' 
        ? `/api/news?source=all&category=all&limit=${limit}&offset=${offset}`
        : `/api/news?category=${validCategory}&source=all&limit=${limit}&offset=${offset}`;

    console.log('Загрузка новостей:', { category: validCategory, page, url });

    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log('Ответ API:', data);
            
            if (data.status === 'success') {
                const tableBody = document.getElementById('news-table-body');
                tableBody.innerHTML = '';

                console.log('Количество новостей:', data.data.length);

                if (data.data.length === 0) {
                    const row = document.createElement('tr');
                    row.innerHTML = `<td colspan="4" style="text-align: center;">Нет данных для отображения</td>`;
                    tableBody.appendChild(row);
                } else {
                    data.data.forEach(news => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${news.published_date ? news.published_date.split(' ')[0] : '-'}</td>
                            <td>${news.source || '-'}</td>
                            <td class="news-title" onclick="openModal(${JSON.stringify(news).replace(/"/g, '&quot;')})"
                            >${news.title || '-'}</td>
                            <td>${news.content || '-'}</td>
                        `;
                        tableBody.appendChild(row);
                    });
                }

                updatePagination(data);
            } else {
                console.error('Ошибка:', data.message);
            }
        })
        .catch(error => console.error('Ошибка сети:', error));
}

// Функция для загрузки доступных категорий
function loadCategories() {
    console.log('Загрузка категорий...');
    fetch('/api/categories')
        .then(response => response.json())
        .then(data => {
            console.log('Категории получены:', data);
            if (data.status === 'success') {
                availableCategories = data.data;
                console.log('Доступные категории:', availableCategories);
                updateCategoryButtons();
            } else {
                console.error('Ошибка загрузки категорий:', data.message);
            }
        })
        .catch(error => console.error('Ошибка сети при загрузке категорий:', error));
}

// Функция для обновления кнопок категорий
function updateCategoryButtons() {
    console.log('Обновление кнопок категорий...');
    const newsTypesContainer = document.querySelector('.news-types');
    if (!newsTypesContainer) {
        console.error('Контейнер кнопок категорий не найден!');
        return;
    }
    
    // Очищаем существующие кнопки
    newsTypesContainer.innerHTML = '';
    
    // Добавляем кнопки для всех категорий
    availableCategories.forEach((category, index) => {
        console.log(`Создание кнопки ${index}:`, category);
        const button = document.createElement('button');
        button.className = 'news-type-btn';
        button.dataset.category = category.id;
        button.textContent = category.name;
        
        // Первая кнопка активна по умолчанию
        if (index === 0) {
            button.classList.add('active');
            currentCategory = category.id;
            console.log('Установлена активная категория:', currentCategory);
        }
        
        // Добавляем обработчик клика
        button.addEventListener('click', function() {
            console.log('Клик по кнопке категории:', this.dataset.category);
            document.querySelector('.news-type-btn.active')?.classList.remove('active');
            this.classList.add('active');
            currentCategory = this.dataset.category;
            currentPage = 1;
            loadNews(currentCategory, currentPage);
        });
        
        newsTypesContainer.appendChild(button);
    });
    
    console.log(`Создано ${availableCategories.length} кнопок категорий`);
}

// Функция обновления пагинации
function updatePagination(data) {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    // Используем поля из API ответа (total_pages и current_page)
    const totalPages = data.total_pages || 0;
    const currentPageNum = data.current_page || 1;

    if (totalPages > 1) {
        if (currentPageNum > 1) {
            const prevBtn = document.createElement('button');
            prevBtn.className = 'pagination-btn';
            prevBtn.textContent = '«';
            prevBtn.addEventListener('click', () => {
                currentPage = currentPageNum - 1;
                loadNews(currentCategory, currentPage);
            });
            pagination.appendChild(prevBtn);
        }

        const maxVisiblePages = 5;
        let startPage = Math.max(1, currentPageNum - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

        if (endPage === totalPages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const btn = document.createElement('button');
            btn.className = `pagination-btn ${i === currentPageNum ? 'active' : ''}`;
            btn.textContent = i;
            btn.addEventListener('click', () => {
                currentPage = i;
                loadNews(currentCategory, i);
            });
            pagination.appendChild(btn);
        }

        if (currentPageNum < totalPages) {
            const nextBtn = document.createElement('button');
            nextBtn.className = 'pagination-btn';
            nextBtn.textContent = '»';
            nextBtn.addEventListener('click', () => {
                currentPage = currentPageNum + 1;
                loadNews(currentCategory, currentPage);
            });
            pagination.appendChild(nextBtn);
        }
    }
}

// Функция открытия модального окна
function openModal(news) {
    const modal = document.getElementById('news-modal');
    document.getElementById('modal-title').textContent = news.title;
    document.getElementById('modal-source').innerHTML = `<strong>Источник:</strong> ${news.source}`;
    document.getElementById('modal-date').innerHTML = `<strong>Дата:</strong> ${news.published_date}`;
    document.getElementById('modal-content').textContent = news.content;

    // Определяем ссылку в зависимости от источника
    let linkUrl = '';
    // Проверяем все возможные поля для ссылок
    const linkFields = [
        'link', 'israil_link', 'telegram_link', 'lenta_link', 'rbc_link', 'gazeta_link', 
        'kommersant_link', 'tsn_link', 'unian_link', 'rt_link', 'cnn_link', 'aljazeera_link', 
        'reuters_link', 'france24_link', 'dw_link', 'euronews_link'
    ];
    
    // Перебираем все возможные поля ссылок
    for (const field of linkFields) {
        if (news[field]) {
            linkUrl = news[field];
            break;
        }
    }

    const modalLink = document.getElementById('modal-link');
    if (linkUrl) {
        modalLink.href = linkUrl;
        modalLink.style.display = 'inline-block';
    } else {
        modalLink.style.display = 'none';
    }

    modal.style.display = 'block';
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Обработчик закрытия окна по клику на крестик
    document.querySelector('.close')?.addEventListener('click', () => {
        document.getElementById('news-modal').style.display = 'none';
    });

    // Обработчик закрытия окна по клику вне контента
    window.addEventListener('click', (event) => {
        const modal = document.getElementById('news-modal');
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
    
    // Загружаем категории и инициализируем интерфейс
    loadCategories();
    
    // Ждем загрузки категорий, затем загружаем новости
    setTimeout(() => {
        if (currentCategory) {
            loadNews(currentCategory, currentPage);
        }
    }, 500);
    
    // Периодическое обновление новостей каждые 5 минут
    setInterval(() => {
        if (currentCategory) {
            loadNews(currentCategory, currentPage);
        }
    }, 300000); // 300000 мс = 5 минут
});
