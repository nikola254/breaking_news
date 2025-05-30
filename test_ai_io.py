import requests

url = "https://api.intelligence.io.solutions/api/v1/models"

headers = {
    "accept": "application/json",
    "Authorization": "Bearer io-v2-eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJvd25lciI6ImVjODQ0MjA4LTVhMjYtNGEyZC1iZjc3LWI5MWM3YWM1NDBkZiIsImV4cCI6NDkwMjAwODMyMn0.KwUhPdVppnVNwtVYbQCUkm8AkbxRipaklZFf20OgWnVjV4Xmo2S4RIX73_j3B5JjdYh4HJI2QS1vvYACcDTxfg",  
}

response = requests.get(url, headers=headers)
data = response.json()
# print(data)
# print(response.text)

for i in range(len(data['data'])):
    name = data['data'][i]['id']
    print(name)
    
import requests

url = "https://api.intelligence.io.solutions/api/v1/chat/completions"

headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer io-v2-eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJvd25lciI6ImVjODQ0MjA4LTVhMjYtNGEyZC1iZjc3LWI5MWM3YWM1NDBkZiIsImV4cCI6NDkwMjAwODMyMn0.KwUhPdVppnVNwtVYbQCUkm8AkbxRipaklZFf20OgWnVjV4Xmo2S4RIX73_j3B5JjdYh4HJI2QS1vvYACcDTxfg"
}

data = {
    "model": "deepseek-ai/DeepSeek-R1",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Hello!"
        }
    ]
}

response = requests.post(url, headers=headers, json=data)
data = response.json()
# print(data)

text = data['choices'][0]['message']['content']
print(text.split('</think>\n\n')[1])