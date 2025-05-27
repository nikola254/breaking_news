function sendToDeepSeek() {
    const prompt = document.getElementById('deepseek-prompt').value;
    const responseBox = document.getElementById('deepseek-response');
    
    // Показываем индикатор загрузки
    responseBox.textContent = '';
    responseBox.classList.add('loading');
    
    fetch('/api/deepseek', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt })
    })
    .then(res => res.json())
    .then(data => {
        responseBox.classList.remove('loading');
        if (data.status === 'success') {
            responseBox.textContent = data.response;
        } else {
            responseBox.innerHTML = `<span style="color: #ff7043;">Ошибка: ${data.message}</span>`;
        }
    })
    .catch(err => {
        responseBox.classList.remove('loading');
        responseBox.innerHTML = `<span style="color: #ff7043;">Сетевая ошибка: ${err.message}</span>`;
    });
}

function sendToOpenRouter() {
    const prompt = document.getElementById('openrouter-prompt').value;
    const responseBox = document.getElementById('openrouter-response');
    const temperature = parseFloat(document.getElementById('temperature').value) || 0.7;
    const maxTokens = parseInt(document.getElementById('max_tokens').value) || 2048;
    const model = document.getElementById('openrouter-model').value;

    responseBox.textContent = '';
    responseBox.classList.add('loading');

    fetch('/api/openrouter', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            prompt: prompt,
            model: model,
            temperature: temperature,
            max_tokens: maxTokens
        })
    })
    .then(res => res.json())
    .then(data => {
        responseBox.classList.remove('loading');
        if (data.status === 'success') {
            responseBox.textContent = data.response;
        } else {
            responseBox.innerHTML = `<span style="color: #ff7043;">Ошибка: ${data.message}</span>`;
        }
    })
    .catch(err => {
        responseBox.classList.remove('loading');
        responseBox.innerHTML = `<span style="color: #ff7043;">Сетевая ошибка: ${err.message}</span>`;
    });
}