import requests
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

TOKEN_URL = "https://auth.atlassian.com/oauth/token"

# Use absolute path for .env file
ENV_FILE_PATH = os.path.join(os.path.dirname(__file__), ".env")

def exchange_code_for_tokens(auth_code):
    """
    Exchanges the authorization code for access and refresh tokens.
    Writes the tokens to the .env file for use by other scripts.
    """
    data = {
        "grant_type": "authorization_code",
        "client_id": os.getenv("JIRA_CLIENT_ID"),
        "client_secret": os.getenv("JIRA_CLIENT_SECRET"),
        "code": auth_code,
        "redirect_uri": os.getenv("JIRA_REDIRECT_URI")
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(TOKEN_URL, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        tokens = response.json()

        # Extract tokens
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']

        #print("Access Token:", access_token)
        #print("Refresh Token:", refresh_token)

        # Read existing lines from .env file
        with open(ENV_FILE_PATH, "r") as env_file:
            lines = env_file.readlines()

        with open(ENV_FILE_PATH, "w") as env_file:
            for line in lines:
                if line.startswith("JIRA_ACCESS_TOKEN="):
                    env_file.write(f"JIRA_ACCESS_TOKEN={access_token}\n")
                elif line.startswith("JIRA_REFRESH_TOKEN="):
                    env_file.write(f"JIRA_REFRESH_TOKEN={refresh_token}\n")
                else:
                    env_file.write(line)

        print("Tokens written to .env file successfully.")
    except requests.exceptions.Timeout:
        print("The request timed out. Please check your network connection and try again.")
    except requests.exceptions.RequestException as e:
        print(f"Error exchanging code for tokens: {e}")
        raise

def refresh_access_token():
    """
    Refreshes the access token using the stored refresh token.
    Replaces the existing access and refresh tokens in the .env file.
    """
    data = {
        "grant_type": "refresh_token",
        "client_id": os.getenv("JIRA_CLIENT_ID"),
        "client_secret": os.getenv("JIRA_CLIENT_SECRET"),
        "refresh_token": os.getenv("JIRA_REFRESH_TOKEN")
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(TOKEN_URL, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        tokens = response.json()

        # Extract tokens
        access_token = tokens['access_token']
        refresh_token = tokens.get('refresh_token', os.getenv("JIRA_REFRESH_TOKEN"))

        print("New Access Token:", access_token)
        print("Refresh Token:", refresh_token)

        # Replace tokens in .env file
        with open(ENV_FILE_PATH, "r") as env_file:
            lines = env_file.readlines()

        with open(ENV_FILE_PATH, "w") as env_file:
            for line in lines:
                if line.startswith("JIRA_ACCESS_TOKEN="):
                    env_file.write(f"JIRA_ACCESS_TOKEN={access_token}\n")
                elif line.startswith("JIRA_REFRESH_TOKEN="):
                    env_file.write(f"JIRA_REFRESH_TOKEN={refresh_token}\n")
                else:
                    env_file.write(line)

        print("Tokens replaced in .env file successfully.")
    except requests.exceptions.Timeout:
        print("The request timed out. Please check your network connection and try again.")
    except requests.exceptions.RequestException as e:
        print(f"Error refreshing access token: {e}")
        raise

if __name__ == "__main__":
    print("Token Manager Script")
    print("1. Exchange Authorization Code for Tokens")
    print("2. Refresh Access Token")
    choice = input("Enter your choice (1/2): ")

    if choice == "1":
        auth_code = input("Enter the authorization code: ")
        exchange_code_for_tokens(auth_code)
    elif choice == "2":
        refresh_access_token()
    else:
        print("Invalid choice. Exiting.")
