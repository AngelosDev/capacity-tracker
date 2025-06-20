import os
import requests
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === Helpers ===

def refresh_access_token():
    logging.info("Refreshing access token...")

    token_url = "https://auth.atlassian.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": os.getenv("JIRA_CLIENT_ID"),
        "client_secret": os.getenv("JIRA_CLIENT_SECRET"),
        "refresh_token": os.getenv("JIRA_REFRESH_TOKEN")
    }
    headers = {"Content-Type": "application/json"}

    response = requests.post(token_url, json=payload, headers=headers)
    response.raise_for_status()
    tokens = response.json()

    # Update the environment file (optional: persist securely elsewhere)
    with open(".env", "r") as f:
        lines = f.readlines()

    with open(".env", "w") as f:
        for line in lines:
            if line.startswith("JIRA_ACCESS_TOKEN="):
                f.write(f"JIRA_ACCESS_TOKEN={tokens['access_token']}\n")
            elif line.startswith("JIRA_REFRESH_TOKEN="):
                f.write(f"JIRA_REFRESH_TOKEN={tokens['refresh_token']}\n")
            else:
                f.write(line)

    os.environ["JIRA_ACCESS_TOKEN"] = tokens["access_token"]
    os.environ["JIRA_REFRESH_TOKEN"] = tokens["refresh_token"]
    logging.info("Access token refreshed and updated.")
    return tokens["access_token"]


def test_authentication():
    access_token = os.getenv("JIRA_ACCESS_TOKEN")
    cloud_id = os.getenv("JIRA_CLOUD_ID")

    if not access_token or not cloud_id:
        raise ValueError("JIRA_ACCESS_TOKEN or JIRA_CLOUD_ID not found in environment.")

    url = f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    response = requests.get(url, headers=headers)

    # If token is expired, refresh and try again
    if response.status_code == 401:
        logging.warning("Access token expired or unauthorized. Attempting to refresh...")
        access_token = refresh_access_token()
        headers["Authorization"] = f"Bearer {access_token}"
        response = requests.get(url, headers=headers)

    response.raise_for_status()
    return response.json()

# === Main Entrypoint ===

def main():
    try:
        user_info = test_authentication()
        logging.info("✅ Authentication successful.")
        logging.info(f"👤 Authenticated as: {user_info['displayName']} ({user_info['emailAddress']})")
    except Exception as e:
        logging.error(f"❌ Authentication test failed: {e}")

if __name__ == "__main__":
    main()
