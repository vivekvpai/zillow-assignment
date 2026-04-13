import requests
import json

# Test the debug endpoint
try:
    response = requests.post(
        'http://localhost:8000/debug',
        json={"query": "test message"},
        headers={'Content-Type': 'application/json'}
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

# Test the main endpoint with a real address
try:
    response = requests.post(
        'http://localhost:8000/get-zestimate',
        json={"query": "What is the Zestimate for 2501 Canterbury Ln E #215, Seattle, WA 98112?"},
        headers={'Content-Type': 'application/json'}
    )
    print(f"\nMain endpoint Status: {response.status_code}")
    print(f"Main endpoint Response: {response.text}")
except Exception as e:
    print(f"Main endpoint Error: {e}")
