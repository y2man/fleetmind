import os
from dotenv import load_dotenv

load_dotenv()
# 5. AFROMESSAGE SMS TEST
# 5. AFROMESSAGE API TEST
print("\n[5] Testing AfroMessage API...")

try:
    import urllib.request
    import urllib.error
    import json

    token = os.getenv("AFROMESSAGE_API_KEY", "").strip()

    if not token:
        raise ValueError("AFROMESSAGE_API_KEY missing from .env")

    request = urllib.request.Request(
        "https://api.afromessage.com/api/balance",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "FleetMind/1.0"
        },
        method="GET"
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode())
            print("HTTP Status:", response.status)
            print("API Response:", data)

    except urllib.error.HTTPError as e:
        print("HTTP Status:", e.code)
        print("API Error:", e.read().decode())

except Exception as e:
    print("FAILED:", type(e).__name__, str(e))