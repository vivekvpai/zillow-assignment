import json
import os
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from litellm import completion
import requests
from dotenv import load_dotenv

load_dotenv()


def load_config():
    with open("config.json", "r", encoding="utf-8") as f:
        return json.load(f)


config_data = load_config()


class Settings(BaseSettings):
    system_api_access_token: str = config_data["system_api_access_token"]
    systematic_api_base_url: str = config_data["systematic_api_base_url"]
    llm_model: str = config_data["llm_model"]
    llm_api_key: str = config_data["llm_api_key"]
    system_prompt: str = config_data["system_prompt"]


settings = Settings()


class ZestimateRequest(BaseModel):
    query: str = Field(..., description="Property address query (e.g., '123 Main St, San Francisco, CA 94102')")

    @field_validator('query')
    @classmethod
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        if len(v.strip()) < 2:
            raise ValueError("Query must be at least 2 characters long")
        return v.strip()


class ChatResponse(BaseModel):
    success: bool
    response_type: str  # "general_chat" or "property_estimate"
    message: Optional[str] = None  # For general chat
    zestimate: Optional[float] = None  # For property estimates
    address: Optional[str] = None  # For property estimates
    radius: Optional[float] = None  # For property estimates
    conversational_response: Optional[str] = None  # For property estimates
    error: Optional[str] = None


class SearchParameters(BaseModel):
    address: str = Field(..., description="Complete address in format 'Street Address, City, State ZIP, USA'")
    radius: float = Field(default=0.06, description="Search radius in miles (default 0.06 miles = 0.1 km)")


app = FastAPI(
    title="Zillow Estimate Agent",
    description="Production-grade API for fetching Zillow estimates using AI-powered query parsing",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


def detect_intent_and_respond(query: str) -> tuple[str, bool]:
    """
    Detect if user wants property info or general chat.
    Returns (response, is_property_query)
    """
    try:
        response = completion(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            messages=[
                {"role": "system", "content": settings.system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1,
            max_tokens=300
        )
        
        content = response.choices[0].message.content.strip()
        
        # Check if response is JSON (property query) or plain text (general chat)
        try:
            # Try to parse as JSON - if successful, it's a property query
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start != -1 and json_end != 0:
                json_str = content[json_start:json_end]
                parsed_data = json.loads(json_str)
                return json_str, True  # Return JSON string and indicate property query
        except json.JSONDecodeError:
            pass
        
        # If not JSON, it's a general chat response
        return content, False
        
    except Exception as e:
        # Fallback to general chat on error
        return "I'm here to help! You can ask me about property estimates or any other questions you have.", False


def parse_query_with_ai(query: str) -> SearchParameters:
    try:
        response = completion(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            messages=[
                {"role": "system", "content": settings.system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("AI response does not contain valid JSON")
        
        json_str = content[json_start:json_end]
        parsed_data = json.loads(json_str)
        
        return SearchParameters(**parsed_data)
    
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse AI response as JSON: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during AI query parsing: {str(e)}"
        )


def fetch_zestimate_from_systematic_api(search_params: SearchParameters) -> Dict[str, Any]:
    try:
        params = {
            "access_token": settings.system_api_access_token,
            "near": search_params.address,
            "radius": str(search_params.radius)
        }
        
        response = requests.get(
            settings.systematic_api_base_url,
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        
        return response.json()
    
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to systematic API timed out"
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found in systematic API"
            )
        elif e.response.status_code == 401:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API token for systematic API"
            )
        else:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Systematic API error: {e.response.text}"
            )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to connect to systematic API: {str(e)}"
        )


def generate_conversational_response(user_query: str, zestimate: float, address: str, radius: int) -> str:
    try:
        response_prompt = f"""You are a helpful real estate assistant. The user asked: "{user_query}"

I found the following property information:
- Address: {address}
- Zestimate: ${zestimate:,.2f}
- Search radius: {radius} mile(s)

Provide a friendly, conversational response to the user with this information. Be helpful and informative."""

        response = completion(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            messages=[
                {"role": "system", "content": "You are a helpful real estate assistant that provides property estimates in a friendly, conversational manner."},
                {"role": "user", "content": response_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"The Zestimate for {address} is ${zestimate:,.2f} (searched within {radius} mile(s))."


@app.get("/")
async def root():
    return {
        "message": "Zillow Estimate Agent API",
        "version": "1.0.0",
        "endpoints": {
            "POST /get-zestimate": "Fetch Zestimate for a property address"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/debug")
async def debug_endpoint(raw_request: dict):
    print(f"Raw request received: {raw_request}")
    return {"received": raw_request}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ZestimateRequest):
    print(f"Received request: {request.query}")  # Debug log
    
    try:
        # Detect intent and get initial response
        ai_response, is_property_query = detect_intent_and_respond(request.query)
        
        if is_property_query:
            # Handle property query
            try:
                # Parse the JSON response for property parameters
                parsed_data = json.loads(ai_response)
                search_params = SearchParameters(**parsed_data)
                
                api_response = fetch_zestimate_from_systematic_api(search_params)
                
                if not api_response.get("success"):
                    return ChatResponse(
                        success=False,
                        response_type="property_estimate",
                        error=f"Property API error: {api_response.get('status', 'Unknown error')}"
                    )
                
                data = api_response.get("bundle", [])
                
                if not data:
                    return ChatResponse(
                        success=False,
                        response_type="property_estimate",
                        error="No property data found for the given address"
                    )
                
                property_data = data[0]
                zestimate = property_data.get("zestimate")
                address = property_data.get("address", search_params.address)
                radius = search_params.radius
                
                conversational_response = generate_conversational_response(
                    request.query,
                    zestimate,
                    address,
                    radius
                )
                
                return ChatResponse(
                    success=True,
                    response_type="property_estimate",
                    zestimate=zestimate,
                    address=address,
                    radius=radius,
                    conversational_response=conversational_response
                )
                
            except json.JSONDecodeError as e:
                return ChatResponse(
                    success=False,
                    response_type="property_estimate",
                    error=f"Failed to parse property parameters: {str(e)}"
                )
        else:
            # Handle general chat
            return ChatResponse(
                success=True,
                response_type="general_chat",
                message=ai_response
            )
    
    except Exception as e:
        return ChatResponse(
            success=False,
            response_type="general_chat",
            error=f"Unexpected error: {str(e)}"
        )


# Keep the old endpoint for backward compatibility
@app.post("/get-zestimate", response_model=ChatResponse)
async def get_zestimate(request: ZestimateRequest):
    # Redirect to new chat endpoint but force property query
    return await chat_endpoint(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
