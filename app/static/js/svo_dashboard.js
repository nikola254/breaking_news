function refreshDashboard() {
    const btn = document.querySelector('.refresh-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading-spinner"></span> Обновление...';
    btn.disabled = true;
    
    // Имитация обновления данных
    setTimeout(() => {
        location.reload();
    }, 2000);
}

// Создание сетевого графа
function createNetworkGraph() {
    const networkContainer = document.getElementById('networkGraph');
    if (!networkContainer) return;
    
    // Очистка контейнера
    networkContainer.innerHTML = '';
    
    const width = networkContainer.offsetWidth;
    const height = 400;
    
    const svg = d3.select('#networkGraph')
        .append('svg')
        .attr('width', width)
        .attr('height', height);
    
    // Данные для сетевого графа - получаем из глобальной переменной
    const networkData = window.networkData;
    
    if (!networkData || !networkData.nodes || !networkData.links) {
        networkContainer.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;">Данные для сетевого графа недоступны</div>';
        return;
    }
    
    // Создание симуляции
    const simulation = d3.forceSimulation(networkData.nodes)
        .force('link', d3.forceLink(networkData.links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));
    
    // Создание связей
    const link = svg.append('g')
        .selectAll('line')
        .data(networkData.links)
        .enter().append('line')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .attr('stroke-width', d => Math.sqrt(d.value) * 2);
    
    // Создание узлов
    const node = svg.append('g')
        .selectAll('circle')
        .data(networkData.nodes)
        .enter().append('circle')
        .attr('r', d => d.size || 8)
        .attr('fill', d => d.color || '#3498db')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
    
    // Добавление подписей к узлам
    const label = svg.append('g')
        .selectAll('text')
        .data(networkData.nodes)
        .enter().append('text')
        .text(d => d.label || d.id)
        .attr('font-size', '12px')
        .attr('font-family', 'Arial, sans-serif')
        .attr('fill', '#333')
        .attr('text-anchor', 'middle')
        .attr('dy', '.35em');
    
    // Добавление всплывающих подсказок
    node.append('title')
        .text(d => `${d.label || d.id}\nВес: ${d.weight || 'N/A'}\nСвязи: ${d.connections || 0}`);
    
    // Обновление позиций при симуляции
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);
        
        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);
        
        label
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    });
    
    // Функции для перетаскивания
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

// Добавляем интерактивность к графикам
document.addEventListener('DOMContentLoaded', function() {
    createNetworkGraph();
    
    const chartImages = document.querySelectorAll('.chart-image');
    
    chartImages.forEach(img => {
        img.addEventListener('click', function() {
            // Открываем график в полном размере
            const modal = document.createElement('div');
            modal.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.9);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
                cursor: pointer;
            `;
            
            const modalImg = document.createElement('img');
            modalImg.src = this.src;
            modalImg.style.cssText = `
                max-width: 95%;
                max-height: 95%;
                border-radius: 10px;
            `;
            
            modal.appendChild(modalImg);
            document.body.appendChild(modal);
            
            modal.addEventListener('click', () => {
                document.body.removeChild(modal);
            });
        });
    });
});

// Автообновление каждые 5 минут
setInterval(refreshDashboard, 300000);