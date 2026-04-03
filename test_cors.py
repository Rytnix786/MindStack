#!/usr/bin/env python3
"""Test CORS configuration on the FastAPI backend."""

import requests
import json

# Test health endpoint with CORS headers like the browser would send
def test_cors():
    print("🔍 Testing CORS configuration...")
    print("-" * 50)
    
    # Test 1: OPTIONS preflight request (what browser sends first)
    print("\n1️⃣  Testing OPTIONS preflight request...")
    try:
        response = requests.options(
            "http://localhost:8000/query",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=5
        )
        print(f"   Status Code: {response.status_code}")
        print(f"   ✅ CORS Headers Present:" if response.status_code == 200 else "   ❌ CORS Headers Missing:")
        
        cors_headers = {
            k: v for k, v in response.headers.items() 
            if k.lower().startswith('access-control')
        }
        for k, v in cors_headers.items():
            print(f"      {k}: {v}")
        
        if response.status_code != 200:
            print(f"   WARNING: Expected 200, got {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Actual POST request (after preflight succeeds)
    print("\n2️⃣  Testing actual POST request with CORS headers...")
    try:
        response = requests.post(
            "http://localhost:8000/query",
            json={"query": "What is the refund policy?"},
            headers={
                "Origin": "http://localhost:8080",
                "Content-Type": "application/json",
            },
            timeout=60
        )
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Query successful!")
            data = response.json()
            print(f"   Query: {data['query']}")
            print(f"   Grounded: {data['answer_grounded']}")
            print(f"   Citations: {len(data['citations'])} chunks")
        else:
            print(f"   ❌ Error: Status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 3: Health check
    print("\n3️⃣  Testing health endpoint...")
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"   Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Backend is healthy: {response.json()}")
        else:
            print(f"   ❌ Unhealthy: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ CORS configuration test complete!")
    return True

if __name__ == "__main__":
    test_cors()
