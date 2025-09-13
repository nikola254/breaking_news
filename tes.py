import os

from openai import OpenAI

api_key = "ZTFlZTgwNGEtZDk0Mi00ZjY2LWI3NmMtZmYzMjdiZDJjYmQ3.606f5e53b3f31fa83a54c7d2da40e0d9"
url = "https://foundation-models.api.cloud.ru/v1"

client = OpenAI(
    api_key=api_key,
    base_url=url
)

response = client.chat.completions.create(
    model="Qwen/Qwen3-Coder-480B-A35B-Instruct",
    max_tokens=5000,
    temperature=0.5,
    presence_penalty=0,
    top_p=0.95,
    messages=[
        {
            "role": "user",
            "content":"Как написать хороший код?"
        }
    ]
)

print(response.choices[0].message.content)