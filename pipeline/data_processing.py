# pipeline/data_processing.py
# Data extraction, normalization, and processing functions for the pipeline.

import pandas as pd
import logging
import os
import requests
import time
from datetime import datetime

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

        df = jira_data_normalized
        df['Project'] = df['fields.project.name']
        df['Key'] = df['key']
        df['Updated'] = pd.to_datetime(df['fields.updated'], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%S')
        df['Created'] = pd.to_datetime(df['fields.created'], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%S')
        df['Summary'] = df['fields.summary']
        df['Description'] = df['fields.description'].apply(lambda adf: extract_text_from_adf(adf) if isinstance(adf, dict) else str(adf) if adf else "")
        if 'fields.project.name' not in df.columns:
            logging.warning("Column 'fields.project.name' is missing. Setting default value.")
            df['fields.project.name'] = "Unknown Project"
        df['Issue Type'] = df['fields.issuetype.name']
        df['Status'] = df['fields.status.name']
        df['Resolution'] = df['fields.resolution.name']
        df['Assignee'] = df['fields.assignee.displayName']
        df['Updated_YearMonth'] = pd.to_datetime(df['Updated']).dt.strftime('%Y-%m')
        df['fields.resolutiondate'] = pd.to_datetime(df['fields.resolutiondate'], errors='coerce', utc=True)
        df['Resolved_YearMonth'] = df['fields.resolutiondate'].dt.strftime('%Y-%m')
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

# Move get_access_token to pipeline/data_processing.py so extract_data can use it without circular import

def get_access_token():
    access_token = os.getenv("JIRA_ACCESS_TOKEN")
    if not access_token:
        logging.error("Access token not found. Please run the 3LO flow once and save the tokens.")
        raise ValueError("Access token not found.")
    expires_at = int(os.getenv("JIRA_TOKEN_EXPIRES_AT", "0"))
    current_time = int(time.time())
    if current_time >= expires_at:
        logging.info("Access token expired. Refreshing...")
        from pipeline.jira_pipeline import refresh_access_token
        refresh_access_token()
    elif expires_at - current_time <= 120:
        logging.info("Access token is about to expire. Refreshing early...")
        from pipeline.jira_pipeline import refresh_access_token
        refresh_access_token()
    return os.getenv("JIRA_ACCESS_TOKEN")

# Add extract_data here so it can be imported by pipeline.jira_pipeline

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
            logging.info(f"Fetched {len(issues)} issues. Total so far: {len(all_issues)}")
            if len(issues) < params['maxResults']:
                break
            start_at += params['maxResults']
        except requests.exceptions.RequestException as e:
            logging.error(f"Error during data extraction: {e}")
            raise
    logging.info("Data extraction successful.")
    return {"issues": all_issues}
