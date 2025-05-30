from flask import Blueprint, jsonify, request, current_app
import os
import requests
import json

# Создаем Blueprint для API внешних сервисов
external_api_bp = Blueprint('external_api', __name__, url_prefix='/api')

# API эндпоинт для отправки промта в DeepSeek
@external_api_bp.route('/deepseek', methods=['POST'])
def deepseek_query():
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
                "max_tokens": data.get('max_tokens', 2048)
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
        
# API эндпоинт для OpenRouter
@external_api_bp.route('/openrouter', methods=['POST'])
def openrouter_query():
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
                "max_tokens": data.get('max_tokens', 2048)
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

# API эндпоинты для работы с AI.IO
@external_api_bp.route('/aiio/models', methods=['GET'])
def aiio_models():
    api_key = current_app.config.get('AIIO_API_KEY')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'AIIO_API_KEY не найден'}), 500

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
    data = request.json
    prompt = data.get('prompt', '')
    model = "deepseek-ai/DeepSeek-R1"  # Фиксированная модель
    system_prompt = data.get('system_prompt', 'You are a helpful assistant.')
    
    api_key = current_app.config.get('AIIO_API_KEY')
    if not api_key:
        return jsonify({'status': 'error', 'message': 'AIIO_API_KEY не найден'}), 500

    try:
        response = requests.post(
            "https://api.intelligence.io.solutions/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "temperature": data.get('temperature', 0.7),
                "max_tokens": data.get('max_tokens', 2048)
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