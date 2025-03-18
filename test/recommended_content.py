import requests

def get_recommendations(email: str, top_k: int = 30, base_url: str = "http://localhost:8001"):
    endpoint = f"{base_url}/recommend"
    params = {"email": email}
    
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        recommendations = response.json()
        
        print("Recommendations fetched successfully!")
        for idx, rec in enumerate(recommendations.get("recommendations", []), start=1):
            print(f"{idx}. ({rec['category']})")
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch recommendations: {e}")
    
if __name__ == "__main__":
    user_email = "user@example.com"
    get_recommendations(user_email, top_k=30)