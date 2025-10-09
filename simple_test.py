import requests

try:
    response = requests.get('http://localhost:5000/', timeout=5)
    print('Main page status:', response.status_code)
except Exception as e:
    print('Error:', e)
