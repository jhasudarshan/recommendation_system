from apscheduler.schedulers.blocking import BlockingScheduler
import requests
from app.config.logger_config import logger
from app.config.config import API_KEY,FETCH_API_URL,PROCESS_API_URL

class NewsScheduler:
    def __init__(self, api_key, fetch_url, process_url, interval_hours=3):
        self.API_KEY = api_key
        self.FETCH_API_URL = fetch_url
        self.PROCESS_API_URL = process_url
        self.interval_hours = interval_hours

        # Configure scheduler
        self.scheduler = BlockingScheduler()

    def fetch_news(self):
        try:
            categories = "health,science,technology,sports,entertainment,business"
            params = {
                "access_key": self.API_KEY,
                "limit": 100,
                "language": "en"
            }

            response = requests.get(self.FETCH_API_URL, params=params)
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

            logger.info(f"Fetched {len(filtered_articles)} valid articles")
            return filtered_articles

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching news: {e}")
            return []

    def send_articles(self, articles):
        for idx, article in enumerate(articles, start=1):
            try:
                response = requests.post(self.PROCESS_API_URL, json=article)
                if response.status_code == 200:
                    logger.info(f"{idx}/{len(articles)} - Sent successfully: {article['title']}")
                else:
                    logger.warning(f"{idx}/{len(articles)} - Failed to send: {article['title']}")
                    logger.warning(f"Response: {response.text}")

            except requests.exceptions.RequestException as e:
                logger.error(f"Error sending article {idx}: {e}")

    def scheduled_job(self):
        logger.info("\n Running Scheduled Job: Fetching and Sending Articles")
        articles = self.fetch_news()
        if articles:
            self.send_articles(articles)
        else:
            logger.info("No valid articles fetched, skipping upload.")

    def start_scheduler(self):
        self.scheduler.add_job(self.scheduled_job, "interval", hours=self.interval_hours)
        logger.info(f"Scheduler started. Fetching articles every {self.interval_hours} hours...")
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("\nScheduler stopped.")
            
scheduler = NewsScheduler(API_KEY, FETCH_API_URL, PROCESS_API_URL)