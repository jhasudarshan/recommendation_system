import requests

url = "http://localhost:8002/feedback/process_metadata_update"
test_event = {
    "user_id": "67d73f922b1cf2f6908dd385",
    "articles": [
        {"id": "67d7527ca11234fb4ee6a32f", "interaction": {"likes": 1, "shares": 0, "clicks": 1}},
        {"id": "67d75298a11234fb4ee6a330", "interaction": {"likes": 0, "shares": 0, "clicks": 1}},
    ]
}

response = requests.post(url, json=test_event)

print("Status Code:", response.status_code)
print("Response:", response.json())