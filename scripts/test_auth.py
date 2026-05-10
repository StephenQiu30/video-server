import sys
import httpx

BASE_URL = "http://localhost:8000"

def test_auth():
    print("Testing registration...")
    try:
        r = httpx.post(f"{BASE_URL}/api/auth/register", json={
            "email": "test@example.com",
            "password": "password123",
            "display_name": "Test User"
        })
        if r.status_code == 200:
            print("Registration success!")
        elif r.status_code == 400 and "already registered" in r.text:
            print("User already exists, continuing to login...")
        else:
            print(f"Registration failed: {r.status_code} {r.text}")
            return

        print("Testing login...")
        r = httpx.post(f"{BASE_URL}/api/auth/login", data={
            "username": "test@example.com",
            "password": "password123"
        })
        if r.status_code == 200:
            token = r.json()["access_token"]
            print(f"Login success! Token: {token[:10]}...")
        else:
            print(f"Login failed: {r.status_code} {r.text}")
            return

        print("Testing /me...")
        r = httpx.get(f"{BASE_URL}/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 200:
            print(f"Me: {r.json()['display_name']}")
        else:
            print(f"Me failed: {r.status_code} {r.text}")

    except Exception as e:
        print(f"Error connecting to API: {e}")

if __name__ == "__main__":
    test_auth()
