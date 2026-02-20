import requests
import json

url = "http://127.0.0.1:8000/audit"
payload = {"video_url": "https://www.youtube.com/watch?v=gj_QyeHTBiI"}
headers = {"Content-Type": "application/json"}

try:
    print(f"Sending request to {url}...")
    response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=600) # Long timeout as VI is slow
    print(f"Status: {response.status_code}")
    print(f"Body: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
