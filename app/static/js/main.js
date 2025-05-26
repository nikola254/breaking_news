// Основной JavaScript файл для приложения NewsAnalytics

// Глобальные переменные
let currentCategory = 'ukraine';
let currentPage = 1;

// Функция для загрузки новостей
function loadNews(category, page) {
    const validCategory = category;
    const limit = 10;
    const offset = (page - 1) * limit;

    fetch(`/api/news?category=${validCategory}&source=all&limit=${limit}&offset=${offset}`)
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const tableBody = document.getElementById('news-table-body');
                tableBody.innerHTML = '';

                if (data.data.length === 0) {
                    const row = document.createElement('tr');
                    row.innerHTML = `<td colspan="4" style="text-align: center;">Нет данных для отображения</td>`;
                    tableBody.appendChild(row);
                } else {
                    data.data.forEach(news => {
                        const row = document.createElement('tr');
                        row.innerHTML = `
                            <td>${news.parsed_date ? news.parsed_date.split(' ')[0] : '-'}</td>
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

// Функция обновления пагинации
function updatePagination(data) {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    if (data.total_pages > 1) {
        if (data.current_page > 1) {
            const prevBtn = document.createElement('button');
            prevBtn.className = 'pagination-btn';
            prevBtn.textContent = '«';
            prevBtn.addEventListener('click', () => {
                currentPage = data.current_page - 1;
                loadNews(currentCategory, currentPage);
            });
            pagination.appendChild(prevBtn);
        }

        const maxVisiblePages = 5;
        let startPage = Math.max(1, data.current_page - Math.floor(maxVisiblePages / 2));
        let endPage = Math.min(data.total_pages, startPage + maxVisiblePages - 1);

        if (endPage === data.total_pages) {
            startPage = Math.max(1, endPage - maxVisiblePages + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const btn = document.createElement('button');
            btn.className = `pagination-btn ${i === data.current_page ? 'active' : ''}`;
            btn.textContent = i;
            btn.addEventListener('click', () => {
                currentPage = i;
                loadNews(currentCategory, i);
            });
            pagination.appendChild(btn);
        }

        if (data.current_page < data.total_pages) {
            const nextBtn = document.createElement('button');
            nextBtn.className = 'pagination-btn';
            nextBtn.textContent = '»';
            nextBtn.addEventListener('click', () => {
                currentPage = data.current_page + 1;
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
    document.getElementById('modal-date').innerHTML = `<strong>Дата:</strong> ${news.parsed_date}`;
    document.getElementById('modal-content').textContent = news.content;

    // Определяем ссылку в зависимости от источника
    let linkUrl = '';
    if (news.link) linkUrl = news.link;
    else if (news.israil_link) linkUrl = news.israil_link;
    else if (news.telegram_link) linkUrl = news.telegram_link;

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
    // Обработчики для кнопок категорий
    document.querySelectorAll('.news-type-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelector('.news-type-btn.active').classList.remove('active');
            this.classList.add('active');
            // Получаем английское значение категории из data-category
            currentCategory = this.dataset.category;
            currentPage = 1;
            loadNews(currentCategory, currentPage);
        });
    });
    
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
    
    // Загружаем новости при загрузке страницы
    loadNews(currentCategory, currentPage);
    
    // Периодическое обновление новостей каждые 5 минут
    setInterval(() => {
        loadNews(currentCategory, currentPage);
    }, 300000); // 300000 мс = 5 минут
});