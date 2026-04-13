import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from litellm import completion
from pydantic import BaseModel, Field, field_validator

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("zillow_agent")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).parent / "config.json"


def load_config() -> dict:
    """Load non-secret configuration from config.json."""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("config.json not found at %s", CONFIG_PATH)
        raise SystemExit(1)
    except json.JSONDecodeError as exc:
        logger.error("config.json contains invalid JSON: %s", exc)
        raise SystemExit(1)


config_data = load_config()

# All configuration (including API keys) lives in config.json for easy editing.
SYSTEM_API_ACCESS_TOKEN = config_data["system_api_access_token"]
LLM_API_KEY = config_data["llm_api_key"]
SYSTEMATIC_API_BASE_URL = config_data["systematic_api_base_url"]
LLM_MODEL = config_data["llm_model"]
SYSTEM_PROMPT = config_data["system_prompt"]

if not SYSTEM_API_ACCESS_TOKEN:
    logger.warning("system_api_access_token is empty in config.json — property lookups will fail.")
if not LLM_API_KEY:
    logger.warning("llm_api_key is empty in config.json — AI features will fail.")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------
class ZestimateRequest(BaseModel):
    query: str = Field(
        ...,
        description="Property address query (e.g., '123 Main St, San Francisco, CA 94102')",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        if len(v.strip()) < 2:
            raise ValueError("Query must be at least 2 characters long")
        return v.strip()


class ChatResponse(BaseModel):
    success: bool
    response_type: str  # "general_chat" or "property_estimate"
    message: Optional[str] = None
    zestimate: Optional[float] = None
    address: Optional[str] = None
    radius: Optional[float] = None
    conversational_response: Optional[str] = None
    error: Optional[str] = None


class SearchParameters(BaseModel):
    address: str = Field(
        ...,
        description="Complete address in format 'Street Address, City, State ZIP, USA'",
    )
    radius: float = Field(
        default=0.03,
        description="Search radius in miles (default 0.03 miles ~ 48 meters)",
    )


# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Zillow Estimate Agent",
    description="AI-powered API for fetching Zillow property estimates",
    version="1.0.0",
)

ALLOWED_ORIGINS = [
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# AI Helpers
# ---------------------------------------------------------------------------
def detect_intent_and_respond(query: str) -> tuple[str, bool]:
    """
    Single LLM call that either returns JSON (property query) or plain text
    (general chat).  Returns (ai_content, is_property_query).
    """
    try:
        response = completion(
            model=LLM_MODEL,
            api_key=LLM_API_KEY,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0.1,
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()

        # Attempt to extract a JSON object from the response.
        # NOTE: This uses a simple brace-matching heuristic. It works for the
        # single flat JSON object the prompt requests, but would break on
        # nested objects or markdown-fenced JSON.
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start != -1 and json_end > json_start:
            json_str = content[json_start:json_end]
            try:
                json.loads(json_str)  # validate
                return json_str, True
            except json.JSONDecodeError:
                pass

        return content, False

    except Exception:
        logger.exception("LLM call failed for query: %s", query)
        return (
            "I'm sorry, I'm having trouble processing your request right now. "
            "Please try again in a moment.",
            False,
        )


def generate_conversational_response(
    user_query: str, zestimate: float, address: str, radius: float
) -> str:
    """Ask the LLM to wrap raw property data in a friendly message."""
    response_prompt = (
        f'You are a helpful real estate assistant. The user asked: "{user_query}"\n\n'
        f"I found the following property information:\n"
        f"- Address: {address}\n"
        f"- Zestimate: ${zestimate:,.2f}\n"
        f"- Search radius: {radius} mile(s)\n\n"
        f"Provide a friendly, conversational response with this information."
    )

    try:
        response = completion(
            model=LLM_MODEL,
            api_key=LLM_API_KEY,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful real estate assistant that provides "
                        "property estimates in a friendly, conversational manner."
                    ),
                },
                {"role": "user", "content": response_prompt},
            ],
            temperature=0.7,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()

    except Exception:
        logger.exception("Failed to generate conversational response")
        return (
            f"The Zestimate for {address} is ${zestimate:,.2f} "
            f"(searched within {radius} mile(s))."
        )


# ---------------------------------------------------------------------------
# BridgeData API Client (async)
# ---------------------------------------------------------------------------
async def fetch_zestimate(search_params: SearchParameters) -> Dict[str, Any]:
    """Fetch Zestimate data from BridgeData Output API (non-blocking)."""
    params = {
        "access_token": SYSTEM_API_ACCESS_TOKEN,
        "near": search_params.address,
        "radius": str(search_params.radius),
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SYSTEMATIC_API_BASE_URL, params=params)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to BridgeData API timed out",
        )
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found in BridgeData API",
            )
        if code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid BridgeData API token",
            )
        raise HTTPException(
            status_code=code,
            detail=f"BridgeData API error: {exc.response.text}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to BridgeData API: {exc}",
        )


# ---------------------------------------------------------------------------
# Result Matching
# ---------------------------------------------------------------------------
def _normalize_address(addr: str) -> str:
    """Lowercase, strip unit/apt markers, collapse whitespace for comparison."""
    import re
    addr = addr.lower().strip()
    # Remove unit/apt designators like '# B', '#3B', 'apt 5', 'unit 12'
    addr = re.sub(r"#\s*\w+", "", addr)
    addr = re.sub(r"\b(apt|unit|ste|suite)\s*\w+", "", addr, flags=re.IGNORECASE)
    # Collapse whitespace
    addr = re.sub(r"\s+", " ", addr).strip()
    return addr


def _find_best_match(bundle: list, query_address: str) -> dict:
    """
    Scan BridgeData results for an exact address match.
    Falls back to the first (nearest) result if no exact match is found.
    """
    normalized_query = _normalize_address(query_address)

    for prop in bundle:
        prop_addr = _normalize_address(prop.get("address", ""))
        if prop_addr == normalized_query:
            logger.info("Exact match found: %s", prop.get("address"))
            return prop

    # Check if the house number at least matches
    query_parts = normalized_query.split()
    if query_parts:
        house_num = query_parts[0]
        for prop in bundle:
            prop_addr = _normalize_address(prop.get("address", ""))
            if prop_addr.startswith(house_num + " "):
                logger.info("House-number match found: %s", prop.get("address"))
                return prop

    logger.info("No exact match; using nearest result: %s", bundle[0].get("address"))
    return bundle[0]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    return {
        "message": "Zillow Estimate Agent API",
        "version": "1.0.0",
        "endpoints": {
            "POST /chat": "Chat with the AI assistant (general + property queries)",
            "POST /get-zestimate": "Legacy — redirects to /chat",
            "GET /health": "Health check",
        },
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ZestimateRequest):
    logger.info("Chat request: %s", request.query)

    try:
        ai_response, is_property_query = detect_intent_and_respond(request.query)

        if not is_property_query:
            return ChatResponse(
                success=True, response_type="general_chat", message=ai_response
            )

        # --- Property query path ---
        try:
            parsed_data = json.loads(ai_response)
            search_params = SearchParameters(**parsed_data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse property params: %s", exc)
            return ChatResponse(
                success=False,
                response_type="property_estimate",
                error=f"Failed to parse property parameters: {exc}",
            )

        api_response = await fetch_zestimate(search_params)

        if not api_response.get("success"):
            return ChatResponse(
                success=False,
                response_type="property_estimate",
                error=f"Property API error: {api_response.get('status', 'Unknown error')}",
            )

        data = api_response.get("bundle", [])
        if not data:
            return ChatResponse(
                success=False,
                response_type="property_estimate",
                error="No property data found for the given address",
            )

        # Pick the best match: prefer an exact address hit over proximity.
        property_data = _find_best_match(data, search_params.address)
        zestimate = property_data.get("zestimate")
        address = property_data.get("address", search_params.address)
        radius = search_params.radius

        conversational_response = generate_conversational_response(
            request.query, zestimate, address, radius
        )

        return ChatResponse(
            success=True,
            response_type="property_estimate",
            zestimate=zestimate,
            address=address,
            radius=radius,
            conversational_response=conversational_response,
        )

    except HTTPException:
        raise  # let FastAPI handle HTTP exceptions
    except Exception as exc:
        logger.exception("Unexpected error in /chat")
        return ChatResponse(
            success=False,
            response_type="general_chat",
            error=f"Unexpected error: {exc}",
        )


@app.post("/get-zestimate", response_model=ChatResponse)
async def get_zestimate(request: ZestimateRequest):
    """Legacy endpoint — delegates to /chat."""
    return await chat_endpoint(request)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
