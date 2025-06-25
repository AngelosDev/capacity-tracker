# This is the main pipeline script, moved from the project root.
# All pipeline logic is here.

import argparse
import yaml
import requests
import pandas as pd
from datetime import datetime
import logging
import anthropic
from dotenv import load_dotenv
import os
import warnings
from openai import OpenAI
import glob
import json
import time
import sys
from dataclasses import dataclass
from typing import List, Optional
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from llm.openai_provider import OpenAIClassifier
from llm.claude_provider import ClaudeClassifier
from llm.bedrock_provider import BedrockClassifier
from pipeline.data_processing import process_data, extract_data, get_access_token

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Helper function to update .env file
def update_env_file(key, value):
    with open(".env", "r") as file:
        lines = file.readlines()
    with open(".env", "w") as file:
        for line in lines:
            if line.startswith(f"{key}="):
                file.write(f"{key}={value}\n")
            else:
                file.write(line)

def main():
    parser = argparse.ArgumentParser(description="JIRA Data Extraction and Processing Pipeline")
    parser.add_argument("--config", default="config/config.yaml", help="Path to the configuration file (YAML or JSON). Defaults to 'config/config.yaml'.")
    parser.add_argument("--interactive", action="store_true", help="Run the script in interactive mode, requiring user confirmation to proceed.")
    parser.add_argument("--max-results", type=int, default=50, help="Maximum number of results to fetch from JIRA API. Defaults to 50.")
    parser.add_argument("--select", type=str, help="Directly pass the selection for non-interactive mode.")
    args = parser.parse_args()

    if args.interactive:
        confirmation = input("You are about to run the script. Do you want to continue? (yes/no): ").strip().lower()
        if confirmation != "yes":
            print("Script execution cancelled.")
            exit()

    # Load configuration
    config = load_config(args.config)
    run_pipeline(args, config)

def run_pipeline(args, config):
    raw_data_path = config['output']['raw_data_path']
    selection = args.select if args.select else select_raw_data_file(raw_data_path)

    if selection == "0":
        # Extract data from JIRA
        jira_data = extract_data(config, args.max_results)
        # Store raw data in a JSON file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        raw_filename = f"jira_raw_data_{timestamp}.json"
        with open(f"{raw_data_path}/{raw_filename}", "w") as json_file:
            json.dump(jira_data, json_file, indent=2)
        logging.info(f"Raw data stored successfully at {raw_data_path}/{raw_filename}.")
    else:
        try:
            selected_file = glob.glob(f"{raw_data_path}/jira_raw_data_*.json")[int(selection) - 1]
            logging.info(f"Using existing raw extract: {selected_file}")
            with open(selected_file, "r") as json_file:
                jira_data = json.load(json_file)
        except (IndexError, ValueError):
            logging.error("Invalid selection. Exiting.")
            sys.exit()

    # Process data
    processed_data = process_data(jira_data)
    # Classify issues
    classified_data = classify_issues(processed_data, config)

def select_raw_data_file(raw_data_path):
    existing_files = glob.glob(f"{raw_data_path}/jira_raw_data_*.json")
    print("Existing raw extracts:")
    for idx, file in enumerate(existing_files, start=1):
        print(f"{idx}. {os.path.basename(file)}")
    print("0. Start extracting from scratch")
    return input("Select an option (0 to start from scratch or file number): ")

def load_config(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    def resolve_env_vars(obj):
        if isinstance(obj, str):
            return os.path.expandvars(obj)
        elif isinstance(obj, dict):
            return {key: resolve_env_vars(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [resolve_env_vars(item) for item in obj]
        return obj
    config = resolve_env_vars(config)
    if 'output' not in config or 'columns' not in config['output']:
        config['output']['columns'] = [
            'Project', 'Key', 'Updated', 'Created', 'Summary', 'Description',
            'Issue Type', 'Status', 'Resolution', 'Assignee'
        ]
    return config

def refresh_access_token():
    url = "https://auth.atlassian.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": os.getenv("JIRA_CLIENT_ID"),
        "client_secret": os.getenv("JIRA_CLIENT_SECRET"),
        "refresh_token": os.getenv("JIRA_REFRESH_TOKEN")
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        tokens = response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        expires_in = tokens.get("expires_in", 3600)
        expires_at = int(time.time()) + expires_in
        os.environ["JIRA_ACCESS_TOKEN"] = access_token
        os.environ["JIRA_REFRESH_TOKEN"] = refresh_token
        os.environ["JIRA_TOKEN_EXPIRES_AT"] = str(expires_at)
        update_env_file("JIRA_ACCESS_TOKEN", access_token)
        update_env_file("JIRA_REFRESH_TOKEN", refresh_token)
        update_env_file("JIRA_TOKEN_EXPIRES_AT", str(expires_at))
        logging.info("Access token refreshed successfully.")
        return access_token
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response status: {e.response.status_code}")
            logging.error(f"Response body: {e.response.text}")
        logging.error(f"Error refreshing access token: {e}")
        raise

def classify_issues(data, config):
    llm_provider = config['classification']['llm_provider']
    llm_api_key = config['classification'].get('llm_api_key')
    categories = config['classification']['categories']
    model_name = config['classification'].get('model')
    if llm_provider == "openai":
        classifier = OpenAIClassifier(api_key=llm_api_key, model=model_name or "gpt-3.5-turbo")
    elif llm_provider == "claude":
        classifier = ClaudeClassifier(api_key=llm_api_key, model=model_name or "claude-v1")
    elif llm_provider == "bedrock":
        classifier = BedrockClassifier(model=model_name or "anthropic.claude-instant-v1")
    else:
        raise ValueError("Unsupported LLM provider")
    processed_issues_file = "output/processed_issues.csv"
    if os.path.exists(processed_issues_file):
        processed_issues = pd.read_csv(processed_issues_file)
    else:
        processed_issues = pd.DataFrame(columns=config['output']['columns'])
    processed_keys = set(processed_issues['Key'])
    unprocessed_data = data[~data['Key'].isin(processed_keys)]
    total_issues = len(unprocessed_data)
    logging.info(f"Starting classification for {total_issues} issues.")
    for idx, row in unprocessed_data.iterrows():
        issue_key = row['Key']
        logging.info(f"Classifying issue {issue_key}. {total_issues - idx - 1} issues remain.")
        row['Category'] = classifier.classify(
            summary=row['Summary'],
            description=row['Description'],
            categories=categories,
            model=model_name
        )
        if row['Category'] != "Unclassified":
            processed_issues = pd.concat([
                processed_issues,
                pd.DataFrame([row], columns=config['output']['columns'])
            ], ignore_index=True)
    processed_issues.to_csv(processed_issues_file, index=False)
    logging.info("Issue classification successful.")
    return processed_issues

if __name__ == "__main__":
    main()
