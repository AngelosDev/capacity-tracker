# JIRA Data Extraction and Processing Pipeline

## Overview
This Python pipeline extracts data from JIRA using the JIRA API, processes the data, classifies issues, and stores the output in a specified format.

---

## Setup

### Prerequisites
- Python 3.8 or higher
- Install required Python packages:
  ```bash
  pip install -r requirements.txt
  ```

### Configuration
1. **Environment Variables**:
   - Copy `.env.example` to `.env` in the root directory.
   - Fill in the required values such as `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`, `LLM_API_KEY`, etc.

2. **Pipeline Configuration**:
   - Copy `example_config.yaml` to `config.yaml` in the root directory.
   - Customize the investment categories and other settings as needed.

### Token Refresh Logic
The script includes logic to refresh the access token when it expires. Ensure the `JIRA_REFRESH_TOKEN` is saved securely in the `.env` file after running the 3LO flow once via browser.

---

## Obtaining Access and Refresh Tokens

To obtain the `access_token` and `refresh_token`, follow these steps:

1. **Run the 3LO Flow via Browser**:
   - Navigate to the authorization URL provided by Atlassian for OAuth 2.0 3LO flow:
     
     [Authorization URL](https://auth.atlassian.com/authorize?audience=api.atlassian.com&client_id=[CLIENT ID]&scope=read%3Ajira-work%20read%3Ajira-user%20offline_access&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback&state=${YOUR_USER_BOUND_VALUE}&response_type=code&prompt=consent)
     
  

2. **Authorize the App**:
   - Log in to your Atlassian account and grant the app access to your JIRA instance.

3. **Retrieve the Authorization Code**:
   - After authorization, you will be redirected to the specified `redirect_uri` which will allow you to copy the code.

4. **Exchange Authorization Code for Tokens**:
   - Use this `code` to exchange for tokens by making a POST request:
     ```bash
     curl -X POST https://auth.atlassian.com/oauth/token \
     -H "Content-Type: application/json" \
     -d '{
       "grant_type": "authorization_code",
       "client_id": "YOUR_CLIENT_ID",
       "client_secret": "YOUR_CLIENT_SECRET",
       "code": "AUTHORIZATION_CODE",
       "redirect_uri": "YOUR_REDIRECT_URI"
     }'
     ```
   - Replace `YOUR_CLIENT_ID`, `YOUR_CLIENT_SECRET`, `AUTHORIZATION_CODE`, and `YOUR_REDIRECT_URI` with the appropriate values.

4. **Save the Tokens**:
   - The response will include `access_token` and `refresh_token`. Save these securely in your `.env` file:
     ```plaintext
     JIRA_ACCESS_TOKEN=your_access_token
     JIRA_REFRESH_TOKEN=your_refresh_token
     ```

---

## Usage

### Running the Pipeline

1. Run the script:
   ```bash
   python jira_pipeline.py
   ```
   By default, the script uses `config.yaml` as the configuration file.

2. Optionally, specify a different configuration file:
   ```bash
   python jira_pipeline.py --config custom_config.yaml
   ```

3. The processed data will be stored in the `output` directory with a timestamped filename.

4. Before running the pipeline script, ensure your environment is updated with the latest tokens:

```bash
source .env
```

### Interactive Mode
To run the script in interactive mode, use the `--interactive` flag. This mode requires user confirmation before proceeding with the pipeline execution.

Example:
```bash
python jira_pipeline.py --interactive
```

### Raw Data Storage
The pipeline now stores raw data extracted from JIRA into a CSV file before processing. Ensure the `raw_data_path` is correctly configured in your `config.yaml` file.


---

## Testing

### Unit Tests
1. Run the unit tests:
   ```bash
   python -m unittest test_jira_pipeline.py
   ```

2. Ensure all tests pass.

---


## Security
- Sensitive information like API tokens is stored securely in `.env`.
- Ensure `.env` is excluded from Git commits using `.gitignore`.

---

## Dependencies

Install dependenices using:
```bash
pip install requirements.txt
```

---

## Token Management

The `token_manager.py` script allows you to manage JIRA tokens. You can:

1. Exchange an authorization code for access and refresh tokens.
2. Refresh the access token using the stored refresh token.

### Steps to Use

1. Ensure your environment variables are set up correctly:
   - `JIRA_CLIENT_ID`
   - `JIRA_CLIENT_SECRET`
   - `JIRA_REDIRECT_URI`
   - `JIRA_REFRESH_TOKEN` (for refreshing tokens)

2. Run the script:

```bash
python token_manager.py
```

3. Follow the prompts:
   - Choose `1` to exchange an authorization code for tokens.
   - Choose `2` to refresh the access token.

4. After running the script, update your terminal environment by running:

```bash
source .env
```

This ensures the updated `.env` file is loaded into the terminal environment.

5. Run the `jira_pipeline.py` script:

```bash
python jira_pipeline.py
```

---

## Standalone Authentication Test

To test the authentication functionality, you can use the standalone script `test_authentication.py`. This script verifies the validity of the access token by calling the `/rest/api/2/myself` endpoint.

### Steps to Run

1. Ensure your environment variables are set up correctly:
   - `JIRA_BASE_URL`
   - `JIRA_CLIENT_ID`
   - `JIRA_CLIENT_SECRET`
   - `JIRA_ACCESS_TOKEN`
   - `JIRA_REFRESH_TOKEN`

2. Run the script:

```bash
python test_authentication.py
```

3. Check the logs for the authentication result. If successful, the authenticated user information will be displayed.

---

## JIRA Data Pipeline

### Usage

1. **Run the script**:
   ```bash
   python3 jira_pipeline.py --config config.yaml
   ```

2. **Interactive Mode**:
   Add `--interactive` to require user confirmation before proceeding.

3. **Output Columns**:
   The output file now includes the following columns:
   - Project
   - Key
   - Updated
   - Created
   - Summary
   - Description
   - Issue Type
   - Status
   - Resolution
   - Assignee

4. **Pagination**:
   The script fetches all Jira issues using pagination.

### Configuration

Ensure `config.yaml` is properly set up with the required fields for JIRA API and output paths.

### Dependencies

Install dependencies using:
```bash
pip install -r requirements.txt
```

