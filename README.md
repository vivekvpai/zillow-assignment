# Zillow Estimate Agent

A production-grade Python REST API agent that uses AI-powered query parsing to fetch Zillow estimates (Zestimates) for US property addresses with >=99% accuracy using the BridgeData Output API.

## Demo

<video src="Zillow AI Chat - Google Chrome 2026-04-13 16-12-11.mp4" width="100%" controls></video>

## Features

- **AI-Powered Query Parsing**: Uses LLM (via litellm) to parse natural language property addresses into structured search parameters
- **Dual-Mode Chat**: Handles both general conversation and property estimate queries in a single `/chat` endpoint
- **Smart Address Matching**: Scans API results for exact address matches instead of blindly using the nearest result
- **REST API**: FastAPI-based async web server with proper CORS support
- **BridgeData API Integration**: Direct integration with BridgeData Output API for Zillow data
- **Chat Frontend**: Clean, responsive browser-based chat interface
- **Configuration-Driven**: Single `config.json` file for API tokens, LLM model, and system prompt
- **Production-Ready**: Async HTTP via `httpx`, structured logging, comprehensive error handling

## Architecture

```
User Message (Frontend or curl)
  -> FastAPI POST /chat
  -> litellm (intent detection + address extraction)
  -> If property query:
       -> BridgeData API (GET with address + radius)
       -> Smart address matching (exact > house-number > nearest)
       -> Conversational LLM response with Zestimate
  -> If general chat:
       -> Direct LLM response
  -> JSON Response to User
```

## Project Structure

```
zillow_ai/
├── backend/
│   ├── .venv/                  # Python virtual environment
│   ├── config.json             # All configuration (API keys, LLM model, system prompt)
│   ├── requirements.txt        # Python dependencies
│   ├── zillow_agent.py         # Main application (FastAPI + agent logic)
│   ├── test_zestimates.py      # Integration tests with known addresses
│   ├── test_api.py             # API endpoint tests
│   └── test_enhanced_chat.py   # Chat feature tests
├── frontend/
│   ├── index.html              # Chat UI
│   ├── script.js               # Chat client logic
│   └── styles.css              # Styling
├── .gitignore
└── README.md
```

## Prerequisites

- Python 3.10 or higher
- A BridgeData Output API access token
- An API key for your LLM provider (Groq, OpenAI, Anthropic, etc.)

## Setup

### 1. Clone the Repository

```bash
git clone <repo-url>
cd zillow_ai
```

### 2. Create & Activate Virtual Environment

```bash
cd backend
python -m venv .venv
```

**Windows (PowerShell):**

```bash
.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**

```bash
.venv\Scripts\activate.bat
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the Application

Edit `backend/config.json` and add your API credentials:

```json
{
  "system_api_access_token": "YOUR_BRIDGEDATA_API_TOKEN",
  "systematic_api_base_url": "https://api.bridgedataoutput.com/api/v2/zestimates_v2/zestimates",
  "llm_model": "groq/moonshotai/kimi-k2-instruct",
  "llm_api_key": "YOUR_LLM_API_KEY",
  "system_prompt": "..."
}
```

**Configuration Fields:**

| Field | Description |
|-------|-------------|
| `system_api_access_token` | Your BridgeData Output API access token |
| `systematic_api_base_url` | Base URL for BridgeData API (pre-configured) |
| `llm_model` | LLM model to use with litellm (e.g., `groq/moonshotai/kimi-k2-instruct`, `gpt-4`) |
| `llm_api_key` | API key for your LLM provider |
| `system_prompt` | System prompt for address parsing (pre-configured) |

> **Note:** The system prompt is already configured to preserve exact addresses and work with the BridgeData API format.

## Running the Application

### Start the Backend

```bash
cd backend
python zillow_agent.py
```

The API server will start on **`http://localhost:8000`**.

### Start the Frontend

Open a second terminal:

```bash
cd frontend
npx serve -p 8081 .
```

Then open **`http://localhost:8081`** in your browser.

### Alternative: Run Backend with Uvicorn Directly

```bash
cd backend
uvicorn zillow_agent:app --reload --host 0.0.0.0 --port 8000
```

## API Usage

### Endpoint: POST /chat

The primary endpoint — handles both general conversation and property estimate queries.

**Request Body:**

```json
{
  "query": "What is the Zestimate for 123 Main St, San Francisco, CA 94102?"
}
```

**Example with curl:**

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the Zestimate for 123 Main St, San Francisco, CA 94102?"}'
```

**Property Estimate Response (200 OK):**

```json
{
  "success": true,
  "response_type": "property_estimate",
  "zestimate": 1250000.0,
  "address": "123 Main St San Francisco CA 94102",
  "radius": 0.03,
  "conversational_response": "The Zestimate for 123 Main St is $1,250,000..."
}
```

**General Chat Response (200 OK):**

```json
{
  "success": true,
  "response_type": "general_chat",
  "message": "Hello! I can help you with property estimates or any other questions."
}
```

**Error Response:**

```json
{
  "success": false,
  "response_type": "property_estimate",
  "error": "No property data found for the given address"
}
```

### Other Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | API information |
| `GET` | `/health` | Health check |
| `POST` | `/get-zestimate` | Legacy endpoint (redirects to `/chat`) |

## Running Tests

The project includes integration tests that validate Zestimates against known addresses:

```bash
cd backend
python test_zestimates.py --verbose
```

Tests use a ±5% tolerance to account for natural Zestimate fluctuations over time.

## Supported Query Formats

The AI-powered parser handles various address formats:

- Full address: `"123 Main St, San Francisco, CA 94102"`
- Natural language: `"What's the Zestimate for 123 Main Street in San Francisco?"`
- With unit numbers: `"14505 Simonds Road NE #C, Kirkland, WA 98034"` (unit stripped automatically)
- With radius: `"Find the value of 456 Oak Ave within 2 miles"`

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Async web framework |
| `uvicorn` | ASGI server |
| `litellm` | Unified LLM API interface |
| `httpx` | Async HTTP client for BridgeData API |
| `python-dotenv` | Environment variable management |
| `pydantic` | Data validation and settings |

## Error Handling

| Scenario | HTTP Status |
|----------|-------------|
| Empty or invalid queries | 400 Bad Request |
| AI parsing failures | 500 Internal Server Error |
| API timeouts | 504 Gateway Timeout |
| Property not found | 404 Not Found |
| Invalid API tokens | 401 Unauthorized |
| API connection failures | 503 Service Unavailable |

## Customization

### Modifying the System Prompt

Edit the `system_prompt` field in `config.json` to customize how the AI parses queries. The prompt should instruct the AI to:

- Parse natural language addresses
- Extract structured search parameters
- Return JSON in the expected format
- Preserve exact house numbers and street names

### Changing the LLM Model

Update the `llm_model` field in `config.json` to use any model supported by litellm (e.g., `gpt-4`, `claude-3-opus`, `groq/llama-3.1-70b-versatile`, etc.).

## Troubleshooting

### Import Errors

Make sure the virtual environment is activated:

```bash
.venv\Scripts\Activate.ps1
```

### Configuration Errors

Verify that `backend/config.json` exists and contains valid JSON with all required fields.

### API Connection Errors

Check that:

- Your API tokens are correct
- The BridgeData API base URL is accessible
- Your network connection is working

### AI Parsing Errors

If the AI fails to parse queries:

- Check that your LLM API key is valid
- Ensure the LLM model is available
- Review the system prompt for clarity

## License

This project is provided as-is for educational and commercial use.
