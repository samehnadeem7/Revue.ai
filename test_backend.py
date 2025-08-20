import requests

def test_backend():
    """Test if backend is accessible"""
    urls_to_test = [
        "https://revue-ai.onrender.com",
        "https://revue-ai.onrender.com/",
        "http://localhost:8000"  # For local testing
    ]
    
    print("🔍 Testing Backend Connectivity...\n")
    
    for url in urls_to_test:
        try:
            print(f"Testing: {url}")
            response = requests.get(f"{url}/", timeout=10)
            if response.status_code == 200:
                print(f"✅ SUCCESS! Status: {response.status_code}")
                print(f"Response: {response.json()}")
                print(f"🎯 Use this URL: {url}\n")
                return url
            else:
                print(f"❌ Status: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ Connection Error")
        except requests.exceptions.Timeout:
            print("❌ Timeout")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        print()
    
    print("❌ No working backend found!")
    print("💡 Check your Render dashboard for the correct URL")

if __name__ == "__main__":
    test_backend()
