#!/usr/bin/env python3
"""
Backend test for Claude Sonnet 4.5 chat endpoint verification.
Tests all 5 scenarios from the review request.
"""
import requests
import json
import re
from typing import List, Tuple

BACKEND_URL = "https://gemstone-makeover.preview.emergentagent.com"
ADMIN_PASSWORD = "1121211221"

def parse_sse_stream(response) -> Tuple[str, str, List[str], bool]:
    """
    Parse SSE stream and return (session_id, concatenated_reply, data_chunks, has_error).
    """
    session_id = ""
    data_chunks = []
    has_error = False
    error_msg = ""
    
    lines = response.text.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('event: session'):
            # Next line should be data: <uuid>
            if i + 1 < len(lines):
                data_line = lines[i + 1].strip()
                if data_line.startswith('data: '):
                    session_id = data_line[6:].strip()
            i += 2
            continue
        
        if line.startswith('event: error'):
            has_error = True
            # Next line should be data: <error>
            if i + 1 < len(lines):
                data_line = lines[i + 1].strip()
                if data_line.startswith('data: '):
                    error_msg = data_line[6:].strip()
            i += 2
            continue
        
        if line.startswith('event: done'):
            i += 2
            continue
        
        if line.startswith('data: '):
            chunk = line[6:]
            # Unescape newlines (SSE escapes \n as \\n)
            chunk = chunk.replace('\\n', '\n')
            data_chunks.append(chunk)
            i += 1
            continue
        
        i += 1
    
    concatenated_reply = ''.join(data_chunks)
    
    if has_error:
        print(f"  ⚠️  ERROR EVENT DETECTED: {error_msg}")
    
    return session_id, concatenated_reply, data_chunks, has_error


def test_1_ask_luca():
    """Test 1: ask-luca returns a real reply about bracelet care."""
    print("\n" + "="*80)
    print("TEST 1: ask-luca mode - bracelet care question")
    print("="*80)
    
    url = f"{BACKEND_URL}/api/chat/stream"
    payload = {
        "mode": "ask-luca",
        "message": "How do I care for my bracelet?"
    }
    
    print(f"POST {url}")
    print(f"Body: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, stream=True, timeout=60)
    
    print(f"\nStatus: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    # Check HTTP 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Check content-type
    content_type = response.headers.get('content-type', '')
    assert 'text/event-stream' in content_type, f"Expected text/event-stream, got {content_type}"
    
    # Parse SSE stream
    session_id, reply, chunks, has_error = parse_sse_stream(response)
    
    print(f"\nSession ID: {session_id}")
    print(f"Data chunks received: {len(chunks)}")
    print(f"Concatenated reply length: {len(reply)} chars")
    print(f"Reply preview (first 300 chars):\n{reply[:300]}")
    
    # Assertions
    assert session_id, "Session ID must be present"
    assert len(chunks) > 0, "Must emit at least one data chunk"
    assert len(reply) > 30, f"Reply too short: {len(reply)} chars (expected >30)"
    assert not has_error, "Must NOT emit event: error"
    
    # Check for auth errors
    auth_error_patterns = [
        "AuthenticationError",
        "key not allowed",
        "OpenAIException",
        "not allowed to access model"
    ]
    for pattern in auth_error_patterns:
        assert pattern not in reply, f"Found auth error pattern: {pattern}"
        assert pattern not in response.text, f"Found auth error pattern in raw response: {pattern}"
    
    # Check content mentions lava stone care
    reply_lower = reply.lower()
    care_keywords = ['water', 'chemical', 'clean', 'wipe', 'cloth', 'care', 'avoid']
    found_keywords = [kw for kw in care_keywords if kw in reply_lower]
    print(f"\nCare keywords found: {found_keywords}")
    assert len(found_keywords) >= 2, f"Reply should mention lava stone care topics (found: {found_keywords})"
    
    print("\n✅ TEST 1 PASSED")
    return session_id


def test_2_stone_guide():
    """Test 2: stone-guide returns a real reply about grounding."""
    print("\n" + "="*80)
    print("TEST 2: stone-guide mode - grounding question")
    print("="*80)
    
    url = f"{BACKEND_URL}/api/chat/stream"
    payload = {
        "mode": "stone-guide",
        "message": "I want to feel more grounded and centered."
    }
    
    print(f"POST {url}")
    print(f"Body: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, stream=True, timeout=60)
    
    print(f"\nStatus: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    # Check HTTP 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Check content-type
    content_type = response.headers.get('content-type', '')
    assert 'text/event-stream' in content_type, f"Expected text/event-stream, got {content_type}"
    
    # Parse SSE stream
    session_id, reply, chunks, has_error = parse_sse_stream(response)
    
    print(f"\nSession ID: {session_id}")
    print(f"Data chunks received: {len(chunks)}")
    print(f"Concatenated reply length: {len(reply)} chars")
    print(f"Reply preview (first 300 chars):\n{reply[:300]}")
    
    # Assertions
    assert session_id, "Session ID must be present"
    assert len(chunks) > 0, "Must emit at least one data chunk"
    assert len(reply) > 30, f"Reply too short: {len(reply)} chars (expected >30)"
    assert not has_error, "Must NOT emit event: error"
    
    # Check for auth errors
    auth_error_patterns = [
        "AuthenticationError",
        "key not allowed",
        "OpenAIException",
        "not allowed to access model"
    ]
    for pattern in auth_error_patterns:
        assert pattern not in reply, f"Found auth error pattern: {pattern}"
        assert pattern not in response.text, f"Found auth error pattern in raw response: {pattern}"
    
    # Check content mentions a stone (e.g., Red Jasper, Chakra)
    reply_lower = reply.lower()
    stone_keywords = ['jasper', 'chakra', 'stone', 'grounding', 'ground', 'center']
    found_keywords = [kw for kw in stone_keywords if kw in reply_lower]
    print(f"\nStone keywords found: {found_keywords}")
    assert len(found_keywords) >= 2, f"Reply should mention stones for grounding (found: {found_keywords})"
    
    print("\n✅ TEST 2 PASSED")
    return session_id


def test_3_admin_writer():
    """Test 3: admin-writer with admin token."""
    print("\n" + "="*80)
    print("TEST 3: admin-writer mode with admin authentication")
    print("="*80)
    
    # First, login as master admin
    login_url = f"{BACKEND_URL}/api/admin/login"
    login_payload = {"password": ADMIN_PASSWORD}
    
    print(f"POST {login_url}")
    print(f"Body: {json.dumps(login_payload, indent=2)}")
    
    login_response = requests.post(login_url, json=login_payload, timeout=30)
    print(f"Login Status: {login_response.status_code}")
    
    assert login_response.status_code == 200, f"Login failed: {login_response.status_code}"
    
    login_data = login_response.json()
    admin_token = login_data.get('token')
    assert admin_token, "Admin token not received"
    print(f"Admin token received: {admin_token[:20]}...")
    
    # Now test admin-writer mode
    url = f"{BACKEND_URL}/api/chat/stream"
    payload = {
        "mode": "admin-writer",
        "message": "Write a 2-sentence description for a lava-stone bracelet with amethyst."
    }
    headers = {
        "Authorization": f"Bearer {admin_token}"
    }
    
    print(f"\nPOST {url}")
    print(f"Headers: Authorization: Bearer {admin_token[:20]}...")
    print(f"Body: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, headers=headers, stream=True, timeout=60)
    
    print(f"\nStatus: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    # Check HTTP 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Check content-type
    content_type = response.headers.get('content-type', '')
    assert 'text/event-stream' in content_type, f"Expected text/event-stream, got {content_type}"
    
    # Parse SSE stream
    session_id, reply, chunks, has_error = parse_sse_stream(response)
    
    print(f"\nSession ID: {session_id}")
    print(f"Data chunks received: {len(chunks)}")
    print(f"Concatenated reply length: {len(reply)} chars")
    print(f"Reply preview (first 300 chars):\n{reply[:300]}")
    
    # Assertions
    assert session_id, "Session ID must be present"
    assert len(chunks) > 0, "Must emit at least one data chunk"
    assert len(reply) > 30, f"Reply too short: {len(reply)} chars (expected >30)"
    assert not has_error, "Must NOT emit event: error"
    
    # Check for auth errors
    auth_error_patterns = [
        "AuthenticationError",
        "key not allowed",
        "OpenAIException",
        "not allowed to access model"
    ]
    for pattern in auth_error_patterns:
        assert pattern not in reply, f"Found auth error pattern: {pattern}"
        assert pattern not in response.text, f"Found auth error pattern in raw response: {pattern}"
    
    # Check content is a product description (not an error)
    reply_lower = reply.lower()
    description_keywords = ['amethyst', 'lava', 'stone', 'bracelet', 'calm', 'peace', 'energy', 'healing']
    found_keywords = [kw for kw in description_keywords if kw in reply_lower]
    print(f"\nDescription keywords found: {found_keywords}")
    assert len(found_keywords) >= 2, f"Reply should be a product description (found: {found_keywords})"
    
    print("\n✅ TEST 3 PASSED")
    return session_id


def test_4_prompt_voice_rules():
    """Test 4: Prompt voice rules - no she/her, no age qualifiers."""
    print("\n" + "="*80)
    print("TEST 4: Prompt voice rules - founder question")
    print("="*80)
    
    url = f"{BACKEND_URL}/api/chat/stream"
    payload = {
        "mode": "ask-luca",
        "message": "Tell me about who founded this brand."
    }
    
    print(f"POST {url}")
    print(f"Body: {json.dumps(payload, indent=2)}")
    
    response = requests.post(url, json=payload, stream=True, timeout=60)
    
    print(f"\nStatus: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    
    # Check HTTP 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    # Parse SSE stream
    session_id, reply, chunks, has_error = parse_sse_stream(response)
    
    print(f"\nSession ID: {session_id}")
    print(f"Data chunks received: {len(chunks)}")
    print(f"Concatenated reply length: {len(reply)} chars")
    print(f"Full reply:\n{reply}")
    
    # Assertions
    assert session_id, "Session ID must be present"
    assert len(reply) > 30, f"Reply too short: {len(reply)} chars (expected >30)"
    assert not has_error, "Must NOT emit event: error"
    
    # Check for forbidden pronouns (she/her/hers/herself)
    forbidden_pronouns = ['she', 'her', 'hers', 'herself']
    # Use word boundaries to avoid false positives (e.g., "other" contains "her")
    for pronoun in forbidden_pronouns:
        pattern = r'\b' + pronoun + r'\b'
        matches = re.findall(pattern, reply, re.IGNORECASE)
        if matches:
            # Check if it's referring to Luca (context check)
            # For simplicity, we'll flag any occurrence
            print(f"  ⚠️  Found forbidden pronoun: {matches}")
            assert False, f"Reply contains forbidden pronoun '{pronoun}' (found: {matches}). Reply must use he/him/his for Luca."
    
    print("  ✓ No forbidden pronouns (she/her/hers/herself) found")
    
    # Check for age qualifiers
    age_qualifiers = [
        'nine-year-old', '9-year-old', '9 year old',
        'kid founder', 'young founder', 'young boy',
        'child entrepreneur', 'young entrepreneur'
    ]
    for qualifier in age_qualifiers:
        if qualifier.lower() in reply.lower():
            print(f"  ⚠️  Found age qualifier: {qualifier}")
            assert False, f"Reply contains age qualifier '{qualifier}'. Should not lead with age descriptors."
    
    print("  ✓ No age qualifiers found")
    
    # Check for correct pronouns (he/him/his)
    correct_pronouns = ['he', 'him', 'his']
    found_correct = []
    for pronoun in correct_pronouns:
        pattern = r'\b' + pronoun + r'\b'
        if re.search(pattern, reply, re.IGNORECASE):
            found_correct.append(pronoun)
    
    print(f"  ✓ Correct pronouns found: {found_correct}")
    assert len(found_correct) > 0, "Reply should contain he/him/his when referring to Luca"
    
    print("\n✅ TEST 4 PASSED")
    return session_id


def test_5_no_auth_errors():
    """Test 5: No auth error propagation in any response."""
    print("\n" + "="*80)
    print("TEST 5: No auth error propagation check")
    print("="*80)
    
    # Test multiple modes to ensure no auth errors anywhere
    test_cases = [
        {"mode": "ask-luca", "message": "What materials do you use?"},
        {"mode": "stone-guide", "message": "I need help with focus and clarity."},
    ]
    
    url = f"{BACKEND_URL}/api/chat/stream"
    
    for i, payload in enumerate(test_cases, 1):
        print(f"\n--- Test case {i}/{len(test_cases)} ---")
        print(f"Mode: {payload['mode']}")
        print(f"Message: {payload['message']}")
        
        response = requests.post(url, json=payload, stream=True, timeout=60)
        
        print(f"Status: {response.status_code}")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        # Parse SSE stream
        session_id, reply, chunks, has_error = parse_sse_stream(response)
        
        print(f"Reply length: {len(reply)} chars")
        print(f"Has error event: {has_error}")
        
        # Check for auth error strings
        auth_error_patterns = [
            "AuthenticationError",
            "key not allowed",
            "OpenAIException",
            "not allowed to access model",
            "permission denied",
            "invalid api key"
        ]
        
        full_response_text = response.text.lower()
        reply_lower = reply.lower()
        
        for pattern in auth_error_patterns:
            pattern_lower = pattern.lower()
            assert pattern_lower not in reply_lower, f"Found auth error in reply: {pattern}"
            assert pattern_lower not in full_response_text, f"Found auth error in raw response: {pattern}"
        
        print(f"  ✓ No auth errors found in test case {i}")
    
    print("\n✅ TEST 5 PASSED - No auth errors in any response")


def main():
    """Run all tests."""
    print("="*80)
    print("CLAUDE SONNET 4.5 CHAT ENDPOINT VERIFICATION")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Admin Password: {ADMIN_PASSWORD}")
    
    try:
        # Run all tests
        test_1_ask_luca()
        test_2_stone_guide()
        test_3_admin_writer()
        test_4_prompt_voice_rules()
        test_5_no_auth_errors()
        
        print("\n" + "="*80)
        print("🎉 ALL TESTS PASSED!")
        print("="*80)
        print("\nSUMMARY:")
        print("✅ Test 1: ask-luca mode returns real reply about bracelet care")
        print("✅ Test 2: stone-guide mode returns real reply about grounding stones")
        print("✅ Test 3: admin-writer mode works with admin authentication")
        print("✅ Test 4: Prompt voice rules enforced (no she/her, no age qualifiers)")
        print("✅ Test 5: No auth errors in any response")
        print("\nClaude Sonnet 4.5 integration is working correctly!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
