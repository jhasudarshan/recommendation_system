import requests

url = "http://localhost:8000/users/log-interest"
data = {
    "email": "user@example.com",
    "interests": [
        {"topic": "Technology", "weight": 0.8},
        {"topic": "Finance", "weight": 0.6}
    ]
}

response = requests.post(url, json=data)

print("Status Code:", response.status_code)
print("Response:", response.json())