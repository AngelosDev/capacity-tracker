# JIRA Data Extraction and Processing Pipeline

## Overview
This Python pipeline extracts data from JIRA using the JIRA API, processes the data, classifies issues, and stores the output in a specified format.

---

## Quick Start (TL;DR)

> **Before running the pipeline, you must first complete the [Authentication steps](#authentication-retrieving-jira-access--refresh-tokens) to obtain your JIRA access and refresh tokens.**

```bash
pip install -r requirements.txt
cp .env.example .env  # Fill in your secrets
python main.py        # Or see below for more options
```

---

## Setup

### Prerequisites
- Python 3.8 or higher
- Install required Python packages:
  ```bash
  pip install -r requirements.txt
  ```

### Environment Variables
- Copy `.env.example` to `.env` in the root directory.
- Fill in the required values such as `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`, `LLM_API_KEY`, etc.

### Configuration
- Copy `config/example_config.yaml` to `config/config.yaml` and customize as needed.

---

## Running the Pipeline

### Main Entrypoint (Recommended)
```bash
python main.py
```
- By default, uses `config/config.yaml`.
- Pass arguments as needed:
  ```bash
  python main.py --config config/config.yaml --interactive
  ```

### Alternative Entrypoint
```bash
python -m pipeline.jira_pipeline --config config/config.yaml
```

### CLI Arguments
- `--config <path>`: Path to config file
- `--interactive`: Require user confirmation before running
- `--max-results <N>`: Limit number of issues fetched

### Output
- Processed data is stored in the `output/` directory with a timestamped filename.
- Raw data is stored in `output/raw_data/`.

---

## Scripts

Utility scripts are in the `scripts/` directory:
- Token management: `python scripts/token_manager.py`
- Authentication test: `python scripts/test_authentication.py`
- OAuth callback server: `python scripts/oauth_callback_server.py`

---

## Authentication: Retrieving JIRA Access & Refresh Tokens

Before running the pipeline, you must obtain valid JIRA access and refresh tokens. Follow these steps:

1. **Start the OAuth Callback Server**
   - In a separate terminal, run:
     ```bash
     python scripts/oauth_callback_server.py
     ```
   - This will start a local server (by default on `http://localhost:8000/callback`) to receive the authorization code. Make sure your `redirect_uri` in the Atlassian app and `.env` matches this URL.

2. **Run the 3LO Flow via Browser**
   - Navigate to the Atlassian OAuth 2.0 3LO authorization URL (replace placeholders with your values):
     ```
     https://auth.atlassian.com/authorize?audience=api.atlassian.com&client_id=YOUR_CLIENT_ID&scope=read%3Ajira-work%20read%3Ajira-user%20offline_access&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fcallback&state=YOUR_USER_BOUND_VALUE&response_type=code&prompt=consent
     ```

3. **Authorize the App**
   - Log in to your Atlassian account and grant the app access to your JIRA instance.

4. **Retrieve the Authorization Code**
   - After authorization, you will be redirected to your `redirect_uri` (e.g., `http://localhost:8000/callback`).
   - Copy the authorization code from the page.

5. **Exchange Authorization Code for Tokens**
   - Use the provided script to exchange the code for tokens:
     ```bash
     python scripts/token_manager.py
     ```
   - Choose option `1` and paste your authorization code when prompted.
   - The script will update your `.env` file with `JIRA_ACCESS_TOKEN` and `JIRA_REFRESH_TOKEN`.

6. **Refresh Tokens as Needed**
   - The pipeline will auto-refresh tokens if expired.
   - To manually refresh, run:
     ```bash
     python scripts/token_manager.py
     ```
   - Choose option `2` to refresh the access token using the stored refresh token.

---

## Testing

### Run All Tests
```bash
python -m unittest discover tests
```

### Run a Specific Test
```bash
python -m unittest tests/test_llm.py
```

---

## Advanced Usage

### LLM Providers
- Supported: OpenAI, Claude, AWS Bedrock
- Configure in `config/config.yaml` under `classification:`
- For Bedrock, no API key is needed; uses AWS credentials chain

### AWS Bedrock Setup
- Set up AWS credentials (`aws configure`)
- IAM user must have Bedrock permissions
- Example config:
  ```yaml
  classification:
    llm_provider: "bedrock"
    model: "anthropic.claude-instant-v1"
  ```

---

## Token Management
- The pipeline will refresh JIRA tokens automatically if expired.
- Use `scripts/token_manager.py` to manually exchange or refresh tokens.

---

## Troubleshooting & FAQ
- **Missing .env or config:** Ensure you have copied and filled in `.env` and `config/config.yaml`.
- **AWS Bedrock errors:** Check your AWS credentials and permissions.
- **Other issues:** See logs for details, or check `PROGRESS.md` for ongoing improvements.

---

## Security
- Sensitive information like API tokens is stored securely in `.env`.
- `.env` is excluded from Git via `.gitignore`.

---

## Contributing
Pull requests and issues are welcome! See `PROGRESS.md` for ongoing work and ideas.

---

