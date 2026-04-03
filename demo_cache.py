#!/usr/bin/env python3
"""Quick demo of query caching in action."""

import requests
import time

API = 'http://localhost:8000'

def demo_cache():
    query = "What is the refund policy?"
    
    print("\n" + "="*70)
    print("🚀 QUERY CACHING LIVE DEMO")
    print("="*70)
    
    # First request
    print(f"\n📝 Query: '{query}'")
    print("\n1️⃣  FIRST REQUEST (cache miss)...")
    start = time.time()
    r1 = requests.post(f'{API}/query', json={'query': query}, timeout=60)
    d1 = r1.json()
    t1 = (time.time() - start) * 1000
    
    print(f"   ✓ Latency: {d1['latency_ms']:.2f}ms")
    print(f"   ✓ Cached: {d1['cached']}")
    print(f"   ✓ LLM Called: {d1['llm_called']}")
    print(f"   ✓ Answer length: {len(d1['answer'])} chars")
    
    time.sleep(0.5)
    
    # Second request (should hit cache)
    print("\n2️⃣  SECOND REQUEST (cache hit)...")
    start = time.time()
    r2 = requests.post(f'{API}/query', json={'query': query}, timeout=60)
    d2 = r2.json()
    t2 = (time.time() - start) * 1000
    
    print(f"   ✓ Latency: {d2['latency_ms']:.2f}ms")
    print(f"   ✓ Cached: {d2['cached']}")
    print(f"   ✓ LLM Called: {d2['llm_called']}")
    
    # Analysis
    print("\n" + "="*70)
    print("📊 RESULTS")
    print("="*70)
    
    speedup = d1['latency_ms'] / d2['latency_ms'] if d2['latency_ms'] > 0 else 999999
    reduction = ((d1['latency_ms'] - d2['latency_ms']) / d1['latency_ms']) * 100
    
    print(f"\n⏱️  Response time:")
    print(f"   First request:  {d1['latency_ms']:>10.2f} ms")
    print(f"   Cached request: {d2['latency_ms']:>10.2f} ms")
    print(f"   Speedup: {speedup:>15.0f}x")
    print(f"   Reduction: {reduction:>13.1f}%")
    
    # Verify identity
    same_answer = d1['answer'] == d2['answer']
    same_grounded = d1['answer_grounded'] == d2['answer_grounded']
    
    print(f"\n✓ Response identity:")
    print(f"   Same answer: {same_answer}")
    print(f"   Same grounded: {same_grounded}")
    
    print("\n" + "="*70)
    if d2['cached'] and speedup > 100:
        print("✅ CACHE IS WORKING PERFECTLY!")
    else:
        print("⚠️  Cache may not be working as expected")
    print("="*70 + "\n")

if __name__ == "__main__":
    try:
        demo_cache()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
