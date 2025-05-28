import requests
import json
import time

def test_api_query(question, provider=None, endpoint="/api/query"):
    """
    Test API by sending a question to specified endpoint with optional provider selection
    """
    # Prepare payload
    payload = {
        'question': question,
        'max_results': 3  # Keep results limited for faster response
    }
    
    # Add provider if specified
    if provider:
        payload['ai_provider'] = provider
    
    print(f"\n----- Testing with question: '{question}' -----")
    print(f"Using provider: {provider or 'default'}")
    print(f"Endpoint: {endpoint}")
    print("Sending request...")
    
    start_time = time.time()
    
    try:
        r = requests.post(f'http://localhost:8000{endpoint}', json=payload, timeout=60)
        elapsed = time.time() - start_time
        
        print(f"Status code: {r.status_code}")
        print(f"Response time: {elapsed:.2f} seconds")
        
        if r.status_code == 200:
            response = r.json()
            
            # Print provider and model info if available
            if 'ai_provider' in response:
                print(f"Provider used: {response['ai_provider']}")
            if 'model_used' in response:
                print(f"Model used: {response['model_used']}")
                
            # Print answer with some formatting
            if 'answer' in response:
                print("\nAnswer:")
                print("=" * 80)
                print(response['answer'])
                print("=" * 80)
            else:
                print("No answer in response")
                
            return response
        else:
            print(f"Error: {r.text}")
            return None
    
    except Exception as e:
        print(f"Request failed: {e}")
        return None

def test_demo_api():
    """Test the demo endpoint (simulated responses)"""
    payload = {
        'question': 'What is the impact of climate change on biodiversity?',
    }

    r = requests.post('http://localhost:8000/api/demo', json=payload)

    print(f"Demo API status code: {r.status_code}")
    print(f"Demo API response: {r.text[:200]}...")  # Show just the start of the response


if __name__ == "__main__":
    # Test getting providers info first
    try:
        r = requests.get('http://localhost:8000/api/providers')
        if r.status_code == 200:
            providers = r.json()
            print("Available providers:")
            print(json.dumps(providers, indent=2))
        else:
            print(f"Could not retrieve providers: {r.status_code}")
    except Exception as e:
        print(f"Error checking providers: {e}")
    
    # Test with OpenAI
    test_api_query(
        "What European research projects focus on sustainable agriculture?", 
        provider="openai"
    )
    
    # Test with Gemini
    test_api_query(
        "Find projects related to quantum computing in the last 5 years", 
        provider="gemini"
    )
    
    # Test demo endpoint too
    print("\n----- Testing Demo Endpoint -----")
    test_demo_api()