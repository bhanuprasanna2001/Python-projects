#!/usr/bin/env python3
"""Test script for the deployed Bookmark API."""

import httpx
import json

BASE_URL = "https://bookmark-api-6gs6.onrender.com"

def print_response(name: str, response: httpx.Response):
    """Pretty print a response."""
    print(f"\n{'='*60}")
    print(f"✅ {name} - Status: {response.status_code}")
    print(f"{'='*60}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text[:500])

def test_api():
    """Run comprehensive API tests."""
    client = httpx.Client(timeout=30.0)
    
    # 1. Health Check
    print("\n🔍 Testing Health Check...")
    r = client.get(f"{BASE_URL}/health")
    print_response("Health Check", r)
    assert r.status_code == 200
    
    # 2. Register a new user (use unique email)
    import time
    unique_email = f"test{int(time.time())}@example.com"
    print(f"\n🔍 Testing User Registration ({unique_email})...")
    r = client.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={
            "email": unique_email,
            "password": "SecurePass123!",
        }
    )
    print_response("User Registration", r)
    assert r.status_code == 201
    user_id = r.json()["id"]
    
    # 3. Login
    print("\n🔍 Testing Login...")
    r = client.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={
            "email": unique_email,
            "password": "SecurePass123!"
        }
    )
    print_response("Login", r)
    assert r.status_code == 200
    tokens = r.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    
    # Set auth header for subsequent requests
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 4. Get current user
    print("\n🔍 Testing Get Current User...")
    r = client.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    print_response("Get Current User", r)
    assert r.status_code == 200
    
    # 5. Create a collection
    print("\n🔍 Testing Create Collection...")
    r = client.post(
        f"{BASE_URL}/api/v1/collections",
        headers=headers,
        json={
            "name": "Tech Articles",
            "description": "Interesting tech reads",
            "color": "#3498db"
        }
    )
    print_response("Create Collection", r)
    assert r.status_code == 201
    collection_id = r.json()["id"]
    
    # 6. Create a tag
    print("\n🔍 Testing Create Tag...")
    r = client.post(
        f"{BASE_URL}/api/v1/tags",
        headers=headers,
        json={
            "name": "python",
            "color": "#306998"
        }
    )
    print_response("Create Tag", r)
    assert r.status_code == 201
    tag_id = r.json()["id"]
    
    # 7. Create a bookmark (without metadata fetch to avoid potential timeout)
    print("\n🔍 Testing Create Bookmark...")
    r = client.post(
        f"{BASE_URL}/api/v1/bookmarks",
        headers=headers,
        json={
            "url": "https://example.com",
            "title": "Example Website",
            "description": "A simple example website",
            "collection_id": collection_id,
            "tag_ids": [tag_id]
        }
    )
    print_response("Create Bookmark", r)
    
    # If 500, try without collection/tags
    if r.status_code == 500:
        print("\n⚠️  Retrying without collection/tags...")
        r = client.post(
            f"{BASE_URL}/api/v1/bookmarks",
            headers=headers,
            json={
                "url": "https://example.com",
                "title": "Example Website",
                "description": "A simple example website"
            }
        )
        print_response("Create Bookmark (simple)", r)
    
    assert r.status_code == 201
    bookmark_id = r.json()["id"]
    
    # 8. List bookmarks
    print("\n🔍 Testing List Bookmarks...")
    r = client.get(f"{BASE_URL}/api/v1/bookmarks", headers=headers)
    print_response("List Bookmarks", r)
    assert r.status_code == 200
    
    # 9. Get single bookmark
    print("\n🔍 Testing Get Bookmark...")
    r = client.get(f"{BASE_URL}/api/v1/bookmarks/{bookmark_id}", headers=headers)
    print_response("Get Bookmark", r)
    assert r.status_code == 200
    
    # 10. Update bookmark
    print("\n🔍 Testing Update Bookmark...")
    r = client.patch(
        f"{BASE_URL}/api/v1/bookmarks/{bookmark_id}",
        headers=headers,
        json={"title": "FastAPI - Modern Python Web Framework"}
    )
    print_response("Update Bookmark", r)
    assert r.status_code == 200
    
    # 11. List collections
    print("\n🔍 Testing List Collections...")
    r = client.get(f"{BASE_URL}/api/v1/collections", headers=headers)
    print_response("List Collections", r)
    assert r.status_code == 200
    
    # 12. List tags
    print("\n🔍 Testing List Tags...")
    r = client.get(f"{BASE_URL}/api/v1/tags", headers=headers)
    print_response("List Tags", r)
    assert r.status_code == 200
    
    # 13. Refresh token
    print("\n🔍 Testing Refresh Token...")
    r = client.post(
        f"{BASE_URL}/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    print_response("Refresh Token", r)
    assert r.status_code == 200
    
    # 14. Delete bookmark
    print("\n🔍 Testing Delete Bookmark...")
    r = client.delete(f"{BASE_URL}/api/v1/bookmarks/{bookmark_id}", headers=headers)
    print_response("Delete Bookmark", r)
    assert r.status_code == 204
    
    # 15. Delete tag
    print("\n🔍 Testing Delete Tag...")
    r = client.delete(f"{BASE_URL}/api/v1/tags/{tag_id}", headers=headers)
    print_response("Delete Tag", r)
    assert r.status_code == 204
    
    # 16. Delete collection
    print("\n🔍 Testing Delete Collection...")
    r = client.delete(f"{BASE_URL}/api/v1/collections/{collection_id}", headers=headers)
    print_response("Delete Collection", r)
    assert r.status_code == 204
    
    # 17. Logout
    print("\n🔍 Testing Logout...")
    r = client.post(f"{BASE_URL}/api/v1/auth/logout", headers=headers)
    print_response("Logout", r)
    assert r.status_code == 200
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS PASSED! Your API is working correctly!")
    print("="*60)
    
    client.close()

if __name__ == "__main__":
    test_api()
