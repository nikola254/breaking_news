"""API для работы с внешними сервисами.

Этот модуль содержит интеграции с внешними AI сервисами:
- DeepSeek API для анализа текста
- OpenRouter API для различных AI моделей
- GigaChat API для обработки естественного языка
"""

from flask import Blueprint, request, jsonify, current_app
import os
import requests
import json

# Создаем Blueprint для API внешних сервисов
external_api_bp = Blueprint('external_api', __name__, url_prefix='/api')

@external_api_bp.route('/deepseek', methods=['POST'])
def deepseek_query():
    """Отправка запроса к DeepSeek API для анализа текста.
    
    Request JSON:
        prompt (str): Текст запроса для анализа
    
    Returns:
        JSON: Ответ от DeepSeek API с результатом анализа
    """
    data = request.json
    prompt = data.get('prompt', '')
    
    api_key = current_app.config.get('DEEPSEEK_API_KEY')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'API ключ не найден'}), 500

    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'status': 'success',
                'response': result['choices'][0]['message']['content'].strip(),
                'usage': result.get('usage', {})
            })
        else:
            return jsonify({
                'status': 'api_error',
                'code': response.status_code,
                'message': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'status': 'server_error',
            'message': str(e)
        }), 500

# API эндпоинт для DeepSeek R1 через OpenRouter
@external_api_bp.route('/deepseek-r1', methods=['POST'])
def deepseek_r1_query():
    """Отправка запроса к DeepSeek R1 через OpenRouter API.
    
    Request JSON:
        prompt (str): Текст запроса для анализа
    
    Returns:
        JSON: Ответ от DeepSeek R1 модели
    """
    data = request.json
    prompt = data.get('prompt', '')
    
    api_key = current_app.config.get('OPENROUTER_DEEPSEEK_R1_API_KEY')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'OPENROUTER_DEEPSEEK_R1_API_KEY не найден'}), 500

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": current_app.config.get('SITE_URL', 'http://localhost:5000'),
                "X-Title": current_app.config.get('SITE_NAME', 'NewsAnalytics')
            },
            json={
                "model": "deepseek/deepseek-r1:free",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": data.get('temperature', 0.7),
                "max_tokens": data.get('max_tokens', 2048),
                "presence_penalty": 0,
                "top_p": 0.95
            },
            timeout=30,
            verify=False
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'status': 'success',
                'response': result['choices'][0]['message']['content'].strip(),
                'usage': result.get('usage', {})
            })
        else:
            return jsonify({
                'status': 'api_error',
                'code': response.status_code,
                'message': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'status': 'server_error',
            'message': str(e)
        }), 500
        
# API эндпоинт для OpenRouter
@external_api_bp.route('/openrouter', methods=['POST'])
def openrouter_query():
    """Отправка запроса к различным AI моделям через OpenRouter API.
    
    Request JSON:
        prompt (str): Текст запроса для анализа
        model (str): Модель для использования (по умолчанию 'google/gemma-3-8b-it:free')
    
    Returns:
        JSON: Ответ от выбранной AI модели
    """
    data = request.json
    prompt = data.get('prompt', '')
    model = data.get('model', 'google/gemma-3-8b-it:free')
    
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'OPENROUTER_API_KEY не найден'}), 500

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": current_app.config.get('SITE_URL', 'http://localhost:5000'),
                "X-Title": current_app.config.get('SITE_NAME', 'NewsAnalytics')
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": data.get('temperature', 0.7),
                "max_tokens": data.get('max_tokens', 2048),
                "presence_penalty": 0,
                "top_p": 0.95
            },
            timeout=30,
            verify=False
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'status': 'success',
                'response': result['choices'][0]['message']['content'].strip(),
                'usage': result.get('usage', {})
            })
        else:
            return jsonify({
                'status': 'api_error',
                'code': response.status_code,
                'message': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'status': 'server_error',
            'message': str(e)
        }), 500

# API эндпоинты для работы с AI.IO
@external_api_bp.route('/aiio/models', methods=['GET'])
def aiio_models():
    """Получение списка доступных моделей от AI.IO API.
    
    Returns:
        JSON: Список доступных AI моделей
    """
    api_key = current_app.config.get('AI_IO_KEY')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'AI_IO_KEY не найден'}), 500

    try:
        response = requests.get(
            "https://api.intelligence.io.solutions/api/v1/models",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'status': 'success',
                'models': result['data']
            })
        else:
            return jsonify({
                'status': 'api_error',
                'code': response.status_code,
                'message': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'status': 'server_error',
            'message': str(e)
        }), 500

@external_api_bp.route('/aiio/chat', methods=['POST'])
def aiio_chat():
    """Отправка запроса к Cloud.ru Foundation Models API для общения с AI моделями.
    
    Request JSON:
        prompt (str): Текст запроса пользователя
        system_prompt (str): Системный промпт (по умолчанию 'You are a helpful assistant.')
    
    Returns:
        JSON: Ответ от Cloud.ru AI модели
    """
    data = request.json
    prompt = data.get('prompt', '')
    system_prompt = data.get('system_prompt', 'You are a helpful assistant.')
    
    api_key = os.getenv('API_KEY')  # Cloud.ru API ключ
    if not api_key:
        return jsonify({'status': 'error', 'message': 'API_KEY (Cloud.ru) не найден'}), 500

    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        response = requests.post(
            "https://foundation-models.api.cloud.ru/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "Qwen/Qwen3-Coder-480B-A35B-Instruct",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": data.get('temperature', 0.7),
                "max_tokens": data.get('max_tokens', 2048),
                "presence_penalty": 0,
                "top_p": 0.95
            },
            timeout=30,
            verify=False
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'status': 'success',
                'response': result['choices'][0]['message']['content'].strip(),
                'usage': result.get('usage', {})
            })
        else:
            return jsonify({
                'status': 'api_error',
                'code': response.status_code,
                'message': response.text
            }), response.status_code
            
    except Exception as e:
        return jsonify({
            'status': 'server_error',
            'message': str(e)
        }), 500