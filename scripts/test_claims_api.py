#!/usr/bin/env python3
"""
Test script for claims API endpoints.
Run this after migration to verify the API is working.
"""

import requests
import sys

API_BASE = "http://localhost:3000/api"

def test_endpoint(name, url, expected_keys=None):
    """Test an API endpoint."""
    print(f"\nTesting {name}...")
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Status: 200")
            if expected_keys:
                for key in expected_keys:
                    if key in data or (isinstance(data, list) and len(data) > 0 and key in data[0]):
                        print(f"  ✓ Has key: {key}")
                    else:
                        print(f"  ✗ Missing key: {key}")
            if isinstance(data, list):
                print(f"  ℹ Count: {len(data)} items")
            return True
        else:
            print(f"  ✗ Status: {response.status_code}")
            print(f"  Error: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"  ✗ Cannot connect to {API_BASE}")
        print(f"  Make sure Kalima server is running (npm run dev)")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def main():
    print("Kalima Claims API Test Suite")
    print("=" * 50)

    tests = [
        ("List all claims", f"{API_BASE}/claims", ["id", "content", "phase"]),
        ("List question-phase claims", f"{API_BASE}/claims?phase=question", ["id", "content"]),
        ("List patterns", f"{API_BASE}/research/patterns", ["id", "description"]),
        ("List morphological patterns", f"{API_BASE}/research/patterns?pattern_type=morphological", ["id"]),
    ]

    results = []
    for name, url, keys in tests:
        results.append(test_endpoint(name, url, keys))

    # Test specific claim if any exist
    print("\nTesting specific claim endpoints...")
    try:
        response = requests.get(f"{API_BASE}/claims", timeout=5)
        if response.status_code == 200:
            claims = response.json()
            if claims and len(claims) > 0:
                claim_id = claims[0]['id']
                print(f"\nUsing claim: {claim_id}")
                results.append(test_endpoint(
                    "Get claim evidence",
                    f"{API_BASE}/claims/{claim_id}/evidence",
                    ["claim_id", "surah", "ayah"]
                ))
                results.append(test_endpoint(
                    "Get claim dependencies",
                    f"{API_BASE}/claims/{claim_id}/dependencies",
                    ["claim", "dependencies"]
                ))
            else:
                print("  ℹ No claims found (run migration first)")
    except Exception as e:
        print(f"  ✗ Error testing specific endpoints: {e}")

    # Summary
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
