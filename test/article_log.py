import requests
import json

FETCH_API_URL = "http://api.mediastack.com/v1/news"
PROCESS_API_URL = "http://localhost:8002/content/process"

API_KEY = "API_KEY"

def fetch_news():
    try:
        categories = "health,science,technology,sports,entertainment,business"
        params = {
            "access_key": API_KEY,
            "limit": 100,
            "language": "en",
            "categories": categories,
        }

        response = requests.get(FETCH_API_URL, params=params)
        response.raise_for_status()

        news_data = response.json().get("data", [])

        filtered_articles = [
            {
                "title": article["title"],
                "description": article["description"],
                "url": article["url"],
                "image_link": article["image"]
            }
            for article in news_data
            if article.get("title") and article.get("description")  # Ensure required fields
        ]

        print(f"Fetched {len(filtered_articles)} valid articles")
        return filtered_articles

    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return []

def send_articles(articles):
    for idx, article in enumerate(articles, start=1):
        try:
            response = requests.post(PROCESS_API_URL, json=article)
            if response.status_code == 200:
                print(f"{idx}/{len(articles)} - Sent successfully: {article['title']}")
            else:
                print(f"{idx}/{len(articles)} - Failed to send: {article['title']}")
                print(f"Response: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"Error sending article {idx}: {e}")

def main():
    articles = fetch_news()
    if articles:
        send_articles(articles)
    else:
        print("No valid articles fetched, skipping upload.")

if __name__ == "__main__":
    main()