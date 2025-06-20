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
from urllib3.exceptions import NotOpenSSLWarning
from openai import OpenAI
import glob
import json
import time
import sys
from dataclasses import dataclass
from typing import List

# Suppress the NotOpenSSLWarning
warnings.simplefilter("ignore", NotOpenSSLWarning)

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

@dataclass
class IssueSchema:
    Project: str
    Key: str
    Updated: str
    Updated_YearMonth: str
    Created: str
    Summary: str
    Description: str
    Issue_Type: str
    Status: str
    Resolution: str
    Resolved_YearMonth: str
    Assignee: str
    Category: str

# Define the main function
def main():
    parser = argparse.ArgumentParser(description="JIRA Data Extraction and Processing Pipeline")
    parser.add_argument("--config", default="config.yaml", help="Path to the configuration file (YAML or JSON). Defaults to 'config.yaml'.")
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

# Load configuration file
def load_config(config_path):
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)

    # Resolve environment variables in the configuration
    def resolve_env_vars(obj):
        if isinstance(obj, str):
            return os.path.expandvars(obj)
        elif isinstance(obj, dict):
            return {key: resolve_env_vars(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [resolve_env_vars(item) for item in obj]
        return obj

    config = resolve_env_vars(config)

    # Ensure output columns are defined
    if 'output' not in config or 'columns' not in config['output']:
        config['output']['columns'] = [
            'Project', 'Key', 'Updated', 'Created', 'Summary', 'Description',
            'Issue Type', 'Status', 'Resolution', 'Assignee'
        ]

    return config

# Refresh the access token

def refresh_access_token():
    url = "https://auth.atlassian.com/oauth/token"
    payload = {
        "grant_type": "refresh_token",
        "client_id": os.getenv("JIRA_CLIENT_ID"),
        "client_secret": os.getenv("JIRA_CLIENT_SECRET"),
        "refresh_token": os.getenv("JIRA_REFRESH_TOKEN")
    }
    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        tokens = response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        expires_in = tokens.get("expires_in", 3600)  # Default to 1 hour if not provided
        expires_at = int(time.time()) + expires_in

        # Save the new tokens and expiry timestamp to environment variables
        os.environ["JIRA_ACCESS_TOKEN"] = access_token
        os.environ["JIRA_REFRESH_TOKEN"] = refresh_token
        os.environ["JIRA_TOKEN_EXPIRES_AT"] = str(expires_at)

        # Update .env file with new tokens and expiry timestamp
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


# Get the access token

def get_access_token():
    access_token = os.getenv("JIRA_ACCESS_TOKEN")

    if not access_token:
        logging.error("Access token not found. Please run the 3LO flow once and save the tokens.")
        raise ValueError("Access token not found.")

    expires_at = int(os.getenv("JIRA_TOKEN_EXPIRES_AT", "0"))
    current_time = int(time.time())

    if current_time >= expires_at:
        logging.info("Access token expired. Refreshing...")
        refresh_access_token()
    elif expires_at - current_time <= 120:
        logging.info("Access token is about to expire. Refreshing early...")
        refresh_access_token()

    return os.getenv("JIRA_ACCESS_TOKEN")

# Extract data from JIRA
def extract_data(config, max_results):
    access_token = get_access_token()
    url = config['jira']['api_url']
    headers = {
        'Authorization': f"Bearer {access_token}"
    }
    params = {
        'jql': f"filter={config['filters']['filter_id']}",
        'startAt': 0,
        'maxResults': max_results,
        'fields': ','.join([
            'project',
            'key',
            'updated',
            'created',
            'summary',
            'description',
            'issuetype',
            'status',
            'resolution',
            'assignee',
            'resolutiondate'
        ])
    }

    all_issues = []
    start_at = 0

    while True:
        try:
            params['startAt'] = start_at
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            issues = data.get("issues", [])
            all_issues.extend(issues)

            # Log progress
            logging.info(f"Fetched {len(issues)} issues. Total so far: {len(all_issues)}")

            # Break if no more issues are returned
            if len(issues) < params['maxResults']:
                break

            start_at += params['maxResults']
        except requests.exceptions.RequestException as e:
            logging.error(f"Error during data extraction: {e}")
            raise

    logging.info("Data extraction successful.")
    return {"issues": all_issues}

# Extract text from JIRA ADF (Atlassian Document Format) descriptions

def extract_text_from_adf(adf):
    if not adf or 'content' not in adf:
        return ""

    def recurse(content):
        result = []
        for block in content:
            block_type = block.get('type')
            if block_type == 'paragraph':
                paragraph = recurse(block.get('content', []))
                result.append("".join(paragraph))
            elif block_type == 'text':
                result.append(block.get('text', ''))
            elif block_type == 'mention':
                mention_text = block.get('attrs', {}).get('text', '')
                result.append(mention_text)
            elif block_type == 'hardBreak':
                result.append("\n")
        return result

    try:
        return "\n\n".join(recurse(adf['content']))
    except Exception as e:
        logging.error(f"Error parsing ADF structure: {e}")
        return ""

# Process data
def process_data(data):
    try:
        issues = data.get("issues", [])
        jira_data_normalized = pd.json_normalize(
            issues,
            record_path=None,
            meta=[
                'fields.project.name',
                'key',
                'fields.updated',
                'fields.created',
                'fields.summary',
            ],
            errors='ignore'
        )

        # Manually extract 'fields.description' into a list
        descriptions = [issue.get('fields', {}).get('description', None) for issue in issues]
        jira_data_normalized['fields.description'] = descriptions

        # Replace the DataFrame creation with the normalized data
        df = jira_data_normalized

        
        df['Project'] = df['fields.project.name']
        df['Key'] = df['key']
        df['Updated'] = pd.to_datetime(df['fields.updated'], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%S')
        df['Created'] = pd.to_datetime(df['fields.created'], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%S')
        df['Summary'] = df['fields.summary']
        # Convert ADF format to plain text for 'fields.description'
        df['Description'] = df['fields.description'].apply(lambda adf: extract_text_from_adf(adf) if isinstance(adf, dict) else str(adf) if adf else "")

        # Log column names for debugging
        logging.debug("Columns in DataFrame:")
        logging.debug(df.columns)

        # Log raw data structure for debugging
        logging.debug("Raw data structure:")
        logging.debug(df.head())

        # Check for missing columns and handle gracefully
        if 'fields.project.name' not in df.columns:
            logging.warning("Column 'fields.project.name' is missing. Setting default value.")
            df['fields.project.name'] = "Unknown Project"

        df['Issue Type'] = df['fields.issuetype.name']
        df['Status'] = df['fields.status.name']
        df['Resolution'] = df['fields.resolution.name']
        df['Assignee'] = df['fields.assignee.displayName']

        # Enrich the data with Updated_YearMonth and Resolved_YearMonth columns
        df['Updated_YearMonth'] = pd.to_datetime(df['Updated']).dt.strftime('%Y-%m')
        # Convert 'fields.resolutiondate' to datetime and handle invalid values
        df['fields.resolutiondate'] = pd.to_datetime(df['fields.resolutiondate'], errors='coerce', utc=True)
        df['Resolved_YearMonth'] = df['fields.resolutiondate'].dt.strftime('%Y-%m')

        # Add a check to ensure the expected columns exist in the DataFrame
        expected_columns = ['fields.project.name', 'key', 'fields.updated', 'fields.created', 'fields.summary', 'fields.description', 'fields.issuetype.name', 'fields.status.name', 'fields.resolution.name', 'fields.assignee.displayName']
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            logging.error(f"Missing columns in the data: {missing_columns}")
            raise KeyError(f"Missing columns: {missing_columns}")

        logging.info("Data processing successful.")
        return df
    except Exception as e:
        logging.error(f"Error during data processing: {e}")
        raise

# Refactor logic for processed_issues

def classify_issues(data, config):
    llm_provider = config['classification']['llm_provider']
    llm_api_key = config['classification']['llm_api_key']
    categories = config['classification']['categories']

    # Read processed issues from a reference file
    processed_issues_file = "output/processed_issues.csv"
    if os.path.exists(processed_issues_file):
        processed_issues = pd.read_csv(processed_issues_file)
    else:
        processed_issues = pd.DataFrame(columns=config['output']['columns'])

    processed_keys = set(processed_issues['Key'])

    # Filter out already processed issues
    unprocessed_data = data[~data['Key'].isin(processed_keys)]

    total_issues = len(unprocessed_data)
    logging.info(f"Starting classification for {total_issues} issues.")

    if llm_provider == "openai":
        client = OpenAI(api_key=llm_api_key)
        for idx, row in unprocessed_data.iterrows():
            issue_key = row['Key']
            logging.info(f"Classifying issue {issue_key}. {total_issues - idx - 1} issues remain.")
            row['Category'] = classify_issue(row, config)
            if row['Category'] != "Unclassified":
                processed_issues = pd.concat([processed_issues, pd.DataFrame([row], columns=config['output']['columns'])], ignore_index=True)

    elif llm_provider == "claude":
        for idx, row in unprocessed_data.iterrows():
            issue_key = row['Key']
            logging.info(f"Classifying issue {issue_key}. {total_issues - idx - 1} issues remain.")
            row['Category'] = classify_issue(row, config)
            if row['Category'] != "Unclassified":
                processed_issues = pd.concat([processed_issues, pd.DataFrame([row], columns=config['output']['columns'])], ignore_index=True)
    else:
        raise ValueError("Unsupported LLM provider")

    # Save all classifications along with other fields to the processed_issues file
    processed_issues.to_csv(processed_issues_file, index=False)

    logging.info("Issue classification successful.")
    return processed_issues

def classify_with_openai(row, categories, client):
    prompt = (
        f"Classify the following Jira issue into one of these categories: {categories}.\n"
        f"Only reply with the category name.\n\n"
        f"Summary: {row['Summary']}\n"
        f"Description: {row['Description'] or 'No description'}"
    )

    try:
        response = client.chat.completions.create(
            model=config['classification'].get('model', 'gpt-3.5-turbo'),
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert JIRA analyst. Your job is to classify JIRA issues into exactly one of the provided business categories. Respond with only the category name. Do not explain or elaborate."
                },

                {"role": "user", "content": prompt}
            ],
            max_tokens=30,
            temperature=0.0
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error classifying issue: {e}")
        return "Unclassified"


def classify_with_claude(row, categories, api_key):
    client = anthropic.Client(api_key)
    prompt = (
        f"Classify the following issue based on its summary and description: \n"
        f"Only reply with the category name.\n\n"
        f"Summary: {row['Summary']}\n"
        f"Description: {row['Description']}\n"
        f"Categories: {categories}"
    )
    response = client.completion(
        prompt=prompt,
        model="claude-v1",
        max_tokens_to_sample=50
    )
    return response['completion'].strip()

# Ensure `config` is passed to the `classify_issue` function
def classify_issue(row, config):
    llm_provider = config['classification']['llm_provider']
    llm_api_key = config['classification']['llm_api_key']
    categories = config['classification']['categories']
    model_name = config['classification'].get('model', 'gpt-3.5-turbo')

    if llm_provider == "openai":
        client = OpenAI(api_key=llm_api_key)
        prompt = (
            f"Classify the following Jira issue into one of these categories: {categories}.\n"
            f"Only reply with the category name.\n\n"
            f"Summary: {row['Summary']}\n"
            f"Description: {row['Description'] or 'No description'}"
        )
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert JIRA analyst. Your job is to classify JIRA issues into exactly one of the provided business categories. Respond with only the category name. Do not explain or elaborate."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=30,
                temperature=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Error classifying issue: {e}")
            return "Unclassified"
    elif llm_provider == "claude":
        client = anthropic.Client(llm_api_key)
        prompt = (
            f"Classify the following issue based on its summary and description: \n"
            f"Only reply with the category name.\n\n"
            f"Summary: {row['Summary']}\n"
            f"Description: {row['Description']}\n"
            f"Categories: {categories}"
        )
        try:
            response = client.completion(
                prompt=prompt,
                model="claude-v1",
                max_tokens_to_sample=50
            )
            return response.get('completion', '').strip()
        except Exception as e:
            logging.error(f"Error classifying issue: {e}")
            return "Unclassified"
    else:
        raise ValueError("Unsupported LLM provider")

# Remove store_output function


if __name__ == "__main__":
    main()
