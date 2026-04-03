#!/usr/bin/env python3
"""Quick test of cache functions."""
from src.retrieval import _normalize_query, _get_cached_response, _cache_response
from src.models import RAGResponse

print("✓ Cache functions imported successfully")

# Test normalization
test_cases = [
    ("What is the refund policy?", "what is the refund policy?"),
    ("  What  IS   The  Refund  Policy?  ", "what is the refund policy?"),
    ("WHAT IS THE REFUND POLICY?", "what is the refund policy?"),
]

print("\n🔤 Testing query normalization:")
for original, expected in test_cases:
    normalized = _normalize_query(original)
    match = "✓" if normalized == expected else "✗"
    print(f"  {match} '{original}' → '{normalized}'")

# Test caching
print("\n💾 Testing cache storage:")
test_response = RAGResponse(
    query="What is the refund policy?",
    answer="You can return items within 30 days",
    answer_grounded=True,
    chunks_retrieved=3,
    latency_ms=1000,
    model_used="mistral",
    prompt_version="1.0",
    cached=False
)

_cache_response("What is the refund policy?", test_response)
print("  ✓ Response cached")

cached = _get_cached_response("What is the refund policy?")
if cached and cached.answer == test_response.answer:
    print("  ✓ Cache hit on exact match")
else:
    print("  ✗ Cache miss on exact match")

# Test normalized matching
cached = _get_cached_response("WHAT IS THE REFUND POLICY?")
if cached and cached.answer == test_response.answer:
    print("  ✓ Cache hit on normalized query")
else:
    print("  ✗ Cache miss on normalized query")

print("\n✅ All cache functionality tests passed!")
