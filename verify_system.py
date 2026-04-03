#!/usr/bin/env python3
"""Final verification that system works correctly."""
import requests

try:
    # Check health
    print("Checking backend health...")
    r = requests.get('http://localhost:8000/health', timeout=5)
    print(f"✓ Backend health: {r.json()}")
    
    # Check query with new field
    print("\nChecking query with cache field...")
    r2 = requests.post('http://localhost:8000/query', json={'query': 'test query'}, timeout=60)
    d = r2.json()
    
    required_fields = ['query', 'answer', 'cached', 'latency_ms', 'answer_grounded']
    missing = [f for f in required_fields if f not in d]
    
    if missing:
        print(f"✗ Missing fields: {missing}")
    else:
        print(f"✓ All fields present")
        print(f"  - cached: {d['cached']}")
        print(f"  - latency_ms: {d['latency_ms']:.2f}")
        print(f"  - answer_grounded: {d['answer_grounded']}")
    
    print("\n✅ System verification complete!")
    
except Exception as e:
    print(f"✗ Error: {e}")
