from ollama import chat

response = chat(
    model='lfm3',
    messages=[{'role': 'user', 'content': 'quantos r tem em strawberry ?'}],
)
print(response.message.content)