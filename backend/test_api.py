import requests
import json

# CONFIGURE YOUR TEST QUERY HERE
USER_QUERY = "What is the Zestimate for 2501 Canterbury Ln E #215, Seattle, WA 98112?"

# API Configuration
API_URL = "http://localhost:8000/get-zestimate"

def test_zestimate_api():
    print("=" * 70)
    print("ZILLOW ESTIMATE AGENT - API TEST")
    print("=" * 70)
    print(f"\nUser Query: {USER_QUERY}")
    print(f"\nCalling API: {API_URL}")
    print("-" * 70)
    
    try:
        # Make the API call
        response = requests.post(
            API_URL,
            json={"query": USER_QUERY},
            timeout=30
        )
        
        # Check response status
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            # Parse and display the response
            data = response.json()
            print("\n" + "=" * 70)
            print("API RESPONSE")
            print("=" * 70)
            print(json.dumps(data, indent=2))
            
            # Extract and display key information
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Success: {data.get('success')}")
            print(f"Zestimate: ${data.get('zestimate', 0):,.2f}" if data.get('zestimate') else "Zestimate: N/A")
            print(f"Address: {data.get('address', 'N/A')}")
            print(f"Radius: {data.get('radius', 'N/A')} mile(s)")
            print(f"\nConversational Response:\n{data.get('conversational_response', 'N/A')}")
            
            if data.get('error'):
                print(f"\nError: {data.get('error')}")
                
        else:
            print(f"\nError: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to the API server.")
        print("Make sure the server is running on http://localhost:8000")
        print("Run: python zillow_agent.py")
        
    except requests.exceptions.Timeout:
        print("\nError: Request timed out")
        
    except Exception as e:
        print(f"\nError: {str(e)}")
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    test_zestimate_api()
