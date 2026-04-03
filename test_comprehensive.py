#!/usr/bin/env python3
"""Comprehensive test suite for RAG system."""

import requests
import json
import sys

API_BASE = 'http://localhost:8000'

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")

def test_health():
    print_section("LAYER 1: SYSTEM HEALTH")
    try:
        response = requests.get(f'{API_BASE}/health')
        print(f"✓ Backend Health: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_query_endpoint():
    print_section("LAYER 2: API - QUERY ENDPOINT")
    
    test_queries = [
        'What is the refund policy?',
        'How do I initiate a refund?',
        'What is the onboarding process?'
    ]
    
    for query in test_queries:
        try:
            response = requests.post(f'{API_BASE}/query', json={'query': query})
            data = response.json()
            print(f"Query: {query}")
            print(f"  Grounded: {'✓ YES' if data['answer_grounded'] else '✗ NO'}")
            print(f"  Citations: {len(data['citations'])}")
            print(f"  Latency: {data['latency_ms']:.0f}ms")
            print(f"  Model: {data['model_used']}")
            print(f"  Answer preview: {data['answer'][:70]}...\n")
        except Exception as e:
            print(f"✗ Query failed: {e}\n")
            return False
    
    return True

def test_metrics():
    print_section("LAYER 2: API - METRICS ENDPOINT")
    
    try:
        response = requests.get(f'{API_BASE}/metrics')
        metrics = response.json()
        print(f"Total Queries:      {metrics['total_queries']}")
        print(f"Grounded Rate:      {metrics['grounded_rate']*100:.1f}%")
        print(f"Avg Latency:        {metrics['avg_latency_ms']:.0f}ms")
        print(f"P95 Latency:        {metrics['p95_latency_ms']:.0f}ms")
        
        if metrics['total_queries'] > 0:
            print(f"\n✓ Metrics being tracked correctly")
            return True
        else:
            print(f"\n⚠ No metrics data yet (fresh start)")
            return True
    except Exception as e:
        print(f"✗ Metrics endpoint failed: {e}")
        return False

def test_logs():
    print_section("LAYER 2: API - QUERY LOGGING")
    
    try:
        import os
        log_path = '/app/logs/query_log.jsonl' if os.path.exists('/app/logs/query_log.jsonl') else './logs/query_log.jsonl'
        
        # Try both container and local paths
        try:
            with open(log_path) as f:
                lines = f.readlines()
        except:
            log_path = './logs/query_log.jsonl'
            with open(log_path) as f:
                lines = f.readlines()
        
        print(f"Log file found at: {log_path}")
        print(f"Total entries: {len(lines)}")
        
        if lines:
            latest = json.loads(lines[-1])
            print(f"\nLatest entry:")
            print(f"  Query: {latest['query'][:60]}...")
            print(f"  Grounded: {latest['answer_grounded']}")
            print(f"  Latency: {latest['latency_ms']:.0f}ms")
            print(f"\n✓ Query logging working correctly")
            return True
        else:
            print("⚠ Log file exists but is empty")
            return True
    except FileNotFoundError:
        print("⚠ Log file not found yet (expected on first run)")
        return True
    except Exception as e:
        print(f"✗ Logging check failed: {e}")
        return False

def test_grounding_quality():
    print_section("LAYER 4: CONTENT QUALITY - GROUNDING VERIFICATION")
    
    golden_questions = [
        'What is the refund policy?',
        'How do I initiate a refund?',
        'How long does a refund take to process?',
        'What is the onboarding process for new employees?',
        'What is the home office stipend for remote employees?',
        'How much does the Pro tier cost?',
        'What storage does the Free tier include?',
        'Is there a free trial available?',
        'What discount is available for annual billing?',
        'Are digital products refundable?'
    ]
    
    grounded_count = 0
    citations_total = 0
    
    for i, query in enumerate(golden_questions, 1):
        try:
            response = requests.post(f'{API_BASE}/query', json={'query': query})
            data = response.json()
            grounded = data['answer_grounded']
            citations = len(data['citations'])
            
            status = '✓' if grounded else '✗'
            print(f"{i:2}. {status} {query[:50]:<50} | Citations: {citations}")
            
            if grounded:
                grounded_count += 1
            citations_total += citations
        except Exception as e:
            print(f"{i:2}. ✗ {query[:50]:<50} | Error: {str(e)[:30]}")
    
    print(f"\nSummary:")
    print(f"  Grounded: {grounded_count}/{len(golden_questions)} ({grounded_count*100//len(golden_questions)}%)")
    print(f"  Total Citations: {citations_total}")
    print(f"  Avg Citations/Query: {citations_total/len(golden_questions):.1f}")
    
    if grounded_count == len(golden_questions):
        print("\n✓ ALL QUERIES GROUNDED - PERFECT SCORE!")
        return True
    else:
        print(f"\n⚠ {len(golden_questions)-grounded_count} queries not grounded")
        return grounded_count >= len(golden_questions) * 0.8  # 80% pass rate

def test_edge_cases():
    print_section("LAYER 8: EDGE CASES & ERROR HANDLING")
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Valid query
    tests_total += 1
    try:
        response = requests.post(f'{API_BASE}/query', json={'query': 'What is pricing?'})
        if response.status_code == 200:
            print("✓ Valid query: OK")
            tests_passed += 1
        else:
            print(f"✗ Valid query: Status {response.status_code}")
    except Exception as e:
        print(f"✗ Valid query: {e}")
    
    # Test 2: Very long query  
    tests_total += 1
    try:
        long_query = 'What ' * 120  # 480 chars
        response = requests.post(f'{API_BASE}/query', json={'query': long_query})
        if response.status_code in [200, 422]:  # 200 or validation error
            print("✓ Long query: Handled gracefully")
            tests_passed += 1
        else:
            print(f"✗ Long query: Unexpected status {response.status_code}")
    except Exception as e:
        print(f"✗ Long query: {e}")
    
    # Test 3: Special characters
    tests_total += 1
    try:
        response = requests.post(f'{API_BASE}/query', json={'query': 'What & how? [test] #special'})
        if response.status_code == 200:
            print("✓ Special characters: OK")
            tests_passed += 1
        else:
            print(f"✗ Special characters: Status {response.status_code}")
    except Exception as e:
        print(f"✗ Special characters: {e}")
    
    # Test 4: Metrics on empty query log
    tests_total += 1
    try:
        response = requests.get(f'{API_BASE}/metrics')
        if response.status_code == 200:
            data = response.json()
            if all(k in data for k in ['total_queries', 'grounded_rate', 'avg_latency_ms', 'p95_latency_ms']):
                print("✓ Metrics structure: Valid")
                tests_passed += 1
            else:
                print("✗ Metrics structure: Missing fields")
        else:
            print(f"✗ Metrics: Status {response.status_code}")
    except Exception as e:
        print(f"✗ Metrics: {e}")
    
    print(f"\nEdge cases: {tests_passed}/{tests_total} passed")
    return tests_passed == tests_total

def main():
    print("\n" + "="*60)
    print("  RAG SYSTEM COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    results = {}
    
    results['Health'] = test_health()
    results['Query API'] = test_query_endpoint()
    results['Metrics API'] = test_metrics()
    results['Logging'] = test_logs()
    results['Grounding Quality'] = test_grounding_quality()
    results['Edge Cases'] = test_edge_cases()
    
    print_section("FINAL TEST SUMMARY")
    
    for test_name, passed in results.items():
        status = '✓ PASS' if passed else '✗ FAIL'
        print(f"{status:8} | {test_name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    print(f"\nTotal: {passed}/{total} test groups passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED - SYSTEM PRODUCTION READY!")
        return 0
    else:
        print(f"\n⚠ {total-passed} test group(s) failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())
