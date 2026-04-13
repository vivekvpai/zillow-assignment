# Zillow Estimate Agent

A production-grade Python REST API agent that uses AI-powered query parsing to fetch Zillow estimates (Zestimates) for US property addresses with >=99% accuracy using the BridgeData Output API.

<video src="Zillow AI Chat - Google Chrome 2026-04-13 16-12-11.mp4"></video>

## Features

- **AI-Powered Query Parsing**: Uses LLM (via litellm) to parse natural language property addresses into structured search parameters
- **REST API**: FastAPI-based web server with POST endpoint for fetching Zestimates
- **BridgeData API Integration**: Direct integration with BridgeData Output API for Zillow data
- **Configuration-Driven**: Easy-to-update JSON configuration for API tokens and system prompts
- **Error Handling**: Comprehensive error handling with meaningful error messages
- **Production-Ready**: Async support, input validation, and proper logging

## Architecture

```
User POST Request
  -> FastAPI Endpoint (/get-zestimate)
  -> litellm (AI with system prompt)
  -> Extracted Clean Address (JSON)
  -> BridgeData API Call (GET)
  -> Zestimate Data
  -> Response to User
```

## Project Structure

```
zillow_ai/
  .venv/                          # Virtual environment
  config.json                     # Configuration file (API tokens, system prompt)
  requirements.txt                # Python dependencies
  zillow_agent.py                 # Main application (FastAPI + agent logic)
  README.md                       # This file
```

## Prerequisites

- Python 3.8 or higher
- API access token for your systematic API (Zillow data source)
- API key for your LLM provider (OpenAI, Anthropic, etc.)

## Setup

### 1. Clone or Navigate to Project Directory

```bash
cd c:/CODE/MY/zillow_ai
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

### 3. Activate Virtual Environment

**Windows (PowerShell):**

```bash
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```bash
.venv\Scripts\activate.bat
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure the Application

Edit `config.json` and replace the placeholder values with your actual API credentials:

```json
{
  "system_api_access_token": "YOUR_BRIDGEDATA_API_TOKEN_HERE",
  "systematic_api_base_url": "https://api.bridgedataoutput.com/api/v2/zestimates_v2/zestimates",
  "llm_model": "gpt-4",
  "llm_api_key": "YOUR_LLM_API_KEY_HERE",
  "system_prompt": "..."
}
```

**Configuration Fields:**

- `system_api_access_token`: Your BridgeData Output API access token
- `systematic_api_base_url`: Base URL for BridgeData API (pre-configured)
- `llm_model`: LLM model to use with litellm (e.g., `gpt-4`, `claude-3`, `gpt-3.5-turbo`)
- `llm_api_key`: API key for your LLM provider (OpenAI, Anthropic, etc.)
- `system_prompt`: System prompt for AI to parse queries (pre-configured for address parsing)

**Note:** The system prompt is already configured to work with BridgeData API format. It removes unit numbers, commas, and special characters to avoid API errors.

## Running the Application

### Start the Server

```bash
python zillow_agent.py
```

The server will start on `http://localhost:8000`

### Alternative: Run with Uvicorn Directly

```bash
uvicorn zillow_agent:app --reload --host 0.0.0.0 --port 8000
```

## API Usage

### Endpoint: POST /get-zestimate

Fetches the Zestimate for a given property address.

**Request Body:**

```json
{
  "query": "123 Main St, San Francisco, CA 94102"
}
```

**Example with curl:**

```bash
curl -X POST "http://localhost:8000/get-zestimate" \
  -H "Content-Type: application/json" \
  -d '{"query": "123 Main St, San Francisco, CA 94102"}'
```

**Example with Python requests:**

```python
import requests

response = requests.post(
    "http://localhost:8000/get-zestimate",
    json={"query": "123 Main St, San Francisco, CA 94102"}
)

print(response.json())
```

**Success Response (200 OK):**

```json
{
  "success": true,
  "zestimate": 1250000.0,
  "address": "123 Main St, San Francisco, CA 94102"
}
```

**Error Response (400 Bad Request):**

```json
{
  "success": false,
  "error": "Query cannot be empty"
}
```

**Error Response (404 Not Found):**

```json
{
  "success": false,
  "error": "Property not found in systematic API"
}
```

**Error Response (500 Internal Server Error):**

```json
{
  "success": false,
  "error": "Failed to parse AI response as JSON: ..."
}
```

### Other Endpoints

- **GET /**: API information
- **GET /health**: Health check endpoint

## Supported Query Formats

The AI-powered parser can handle various address formats:

- Full address: `"123 Main St, San Francisco, CA 94102"`
- Natural language: `"What's the Zestimate for 123 Main Street in San Francisco?"`
- Partial address: `"Main St 123 in SF California"`
- ZIP code only: `"94102"` (if supported by systematic API)

## Error Handling

The application handles various error scenarios:

- **Empty or invalid queries**: Returns 400 Bad Request
- **AI parsing failures**: Returns 500 Internal Server Error
- **API timeouts**: Returns 504 Gateway Timeout
- **Property not found**: Returns 404 Not Found
- **Invalid API tokens**: Returns 401 Unauthorized
- **API connection failures**: Returns 503 Service Unavailable

## Dependencies

- `fastapi`: Modern, fast web framework
- `uvicorn`: ASGI server
- `litellm`: Unified LLM API interface
- `python-dotenv`: Environment variable management
- `requests`: HTTP client for API calls
- `pydantic`: Data validation

## Customization

### Modifying the System Prompt

Edit the `system_prompt` field in `config.json` to customize how the AI parses queries. The prompt should instruct the AI to:

- Parse natural language addresses
- Extract structured search parameters
- Return JSON in the expected format
- Ensure high accuracy

### Changing the LLM Model

Update the `llm_model` field in `config.json` to use a different LLM model supported by litellm (e.g., `claude-3-opus`, `gpt-3.5-turbo`, etc.).

## Troubleshooting

### Import Errors

Make sure the virtual environment is activated:

```bash
.venv\Scripts\Activate.ps1
```

### Configuration Errors

Verify that `config.json` exists and contains valid JSON with all required fields.

### API Connection Errors

Check that:

- Your API tokens are correct
- The systematic API base URL is accessible
- Your network connection is working

### AI Parsing Errors

If the AI fails to parse queries:

- Check that your LLM API key is valid
- Ensure the LLM model is available
- Review the system prompt for clarity

## Production Deployment

For production deployment, consider:

1. **Environment Variables**: Move sensitive credentials to environment variables
2. **HTTPS**: Use a reverse proxy (nginx, Apache) with SSL/TLS
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Logging**: Add comprehensive logging for monitoring
5. **Monitoring**: Set up health checks and alerting
6. **Scaling**: Use a production ASGI server with multiple workers

Example production command:

```bash
uvicorn zillow_agent:app --workers 4 --host 0.0.0.0 --port 8000
```

## License

This project is provided as-is for educational and commercial use.

## Support

For issues or questions, please refer to the project documentation or contact the development team.
