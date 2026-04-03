#!/usr/bin/env python3
"""Cache demo with unique query to ensure first miss."""

import requests
import time
import random
import string

API = 'http://localhost:8000'

def demo():
    # Use unique query to guarantee no cache hit
    unique_id = ''.join(random.choices(string.ascii_lowercase, k=8))
    query = f"Tell me about product {unique_id}"
    
    print("\n" + "="*70)
    print("🚀 CACHE DEMONSTRATION - FRESH QUERY")
    print("="*70)
    print(f"\n📝 Unique query: '{query}'")
    
    # First request
    print("\n1️⃣  FIRST REQUEST (guaranteed cache miss)...")
    start = time.time()
    r1 = requests.post(f'{API}/query', json={'query': query}, timeout=60)
    d1 = r1.json()
    t1 = (time.time() - start) * 1000
    
    print(f"   Latency: {d1['latency_ms']:.2f}ms")
    print(f"   Cached: {d1['cached']}")
    print(f"   LLMCalled: {d1['llm_called']}")
    
    time.sleep(0.2)
    
    # Second request (should hit cache)
    print("\n2️⃣  SECOND REQUEST (should be instant)...")
    start = time.time()
    r2 = requests.post(f'{API}/query', json={'query': query}, timeout=60)
    d2 = r2.json()
    t2 = (time.time() - start) * 1000
    
    print(f"   Latency: {d2['latency_ms']:.2f}ms")
    print(f"   Cached: {d2['cached']}")
    print(f"   LLM Called: {d2['llm_called']}")
    
    # Summary
    print("\n" + "="*70)
    
    if d1['cached'] == False and d2['cached'] == True:
        speedup = d1['latency_ms'] / max(d2['latency_ms'], 0.001)
        print(f"✅ CACHE WORKING!")
        print(f"\n   First:  {d1['latency_ms']:.2f}ms (miss)")
        print(f"   Second: {d2['latency_ms']:.2f}ms (cache hit)")
        print(f"   Speedup: {speedup:.1f}x faster")
    else:
        print(f"ℹ️  Cache status:")
        print(f"   First request cached: {d1['cached']}")
        print(f"   Second request cached: {d2['cached']}")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    demo()
