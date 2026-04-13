import requests
import json

def test_chat(message):
    try:
        response = requests.post(
            'http://localhost:8000/chat',
            json={"query": message},
            headers={'Content-Type': 'application/json'}
        )
        print(f"\nQuery: {message}")
        print(f"Status: {response.status_code}")
        if response.ok:
            data = response.json()
            print(f"Response Type: {data.get('response_type')}")
            print(f"Success: {data.get('success')}")
            if data.get('response_type') == 'general_chat':
                print(f"AI Response: {data.get('message')}")
            elif data.get('response_type') == 'property_estimate':
                print(f"Zestimate: ${data.get('zestimate', 0):,.2f}" if data.get('zestimate') else "Zestimate: N/A")
                print(f"Address: {data.get('address', 'N/A')}")
                print(f"Conversational: {data.get('conversational_response', 'N/A')[:100]}...")
            if data.get('error'):
                print(f"Error: {data.get('error')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")

# Test general chat
print("=== TESTING GENERAL CHAT ===")
test_chat("Hello! How are you today?")
test_chat("What can you help me with?")
test_chat("Tell me a joke")

# Test property queries
print("\n\n=== TESTING PROPERTY QUERIES ===")
test_chat("What is the Zestimate for 2501 Canterbury Ln E #215, Seattle, WA 98112?")
test_chat("How much is 123 Main St worth?")
test_chat("Find the value of 456 Oak Avenue, Portland, OR")

# Test ambiguous queries
print("\n\n=== TESTING AMBIGUOUS QUERIES ===")
test_chat("houses")
test_chat("real estate")
