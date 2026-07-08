"""
Backend test for Essential Gemstones per-user chat memory endpoints.
Tests scenarios A-G as specified in the review request.
"""
import os
import requests
import uuid
import json
from typing import Optional

# Get backend URL from environment
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://gemstone-makeover.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api"

print(f"Testing backend at: {API_BASE}")
print("=" * 80)


def consume_sse_stream(response) -> tuple[Optional[str], str, list[str]]:
    """
    Consume SSE stream and return (sessionId, full_reply, chunks).
    """
    session_id = None
    chunks = []
    full_reply = ""
    
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event: session"):
            continue
        if line.startswith("data: "):
            data = line[6:]  # Remove "data: " prefix
            if session_id is None and not data.startswith("{"):
                # First data line after session event is the session ID
                session_id = data
            else:
                chunks.append(data)
                # Unescape newlines
                full_reply += data.replace("\\n", "\n")
        elif line.startswith("event: done"):
            break
    
    return session_id, full_reply, chunks


def test_scenario_a_anonymous_per_browser_isolation():
    """
    A. Anonymous per-browser isolation
    1. Create random X-Client-Id A, POST /api/chat/stream with ask-luca
    2. GET /api/chat/sessions with X-Client-Id A → contains sessionId
    3. Create different X-Client-Id B, GET /api/chat/sessions → does NOT contain A's session
    4. GET /api/chat/session/{A_id} with X-Client-Id B → 403
    5. GET /api/chat/session/{A_id} with X-Client-Id A → 200
    """
    print("\n### SCENARIO A: Anonymous per-browser isolation")
    
    # Test 1: Create session with X-Client-Id A
    client_id_a = f"test-client-{uuid.uuid4()}"
    print(f"\n[A1] Creating session with X-Client-Id: {client_id_a}")
    
    resp = requests.post(
        f"{API_BASE}/chat/stream",
        json={"mode": "ask-luca", "message": "Hello, question about shipping."},
        headers={"X-Client-Id": client_id_a},
        stream=True,
        timeout=30
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text[:200] if hasattr(resp, 'text') else ''}"
    content_type = resp.headers.get("content-type", "")
    assert "text/event-stream" in content_type, f"Expected SSE content-type, got: {content_type}"
    
    session_id_a, reply_a, chunks_a = consume_sse_stream(resp)
    assert session_id_a, "Session ID not found in SSE stream"
    assert len(reply_a) > 30, f"Reply too short: {len(reply_a)} chars"
    print(f"✅ Session created: {session_id_a}")
    print(f"   Reply length: {len(reply_a)} chars, chunks: {len(chunks_a)}")
    
    # Test 2: List sessions with X-Client-Id A
    print(f"\n[A2] Listing sessions with X-Client-Id A")
    resp = requests.get(
        f"{API_BASE}/chat/sessions",
        params={"mode": "ask-luca"},
        headers={"X-Client-Id": client_id_a},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    sessions_a = resp.json()
    assert isinstance(sessions_a, list), "Expected list of sessions"
    
    session_ids_a = [s["id"] for s in sessions_a]
    assert session_id_a in session_ids_a, f"Session {session_id_a} not found in list"
    
    # Check session structure
    session_obj = next(s for s in sessions_a if s["id"] == session_id_a)
    assert session_obj.get("title"), "Title should be non-empty"
    assert session_obj.get("messageCount", 0) >= 1, "Message count should be >= 1"
    print(f"✅ Session found in list: title='{session_obj['title']}', messageCount={session_obj['messageCount']}")
    
    # Test 3: Create different X-Client-Id B and list sessions
    client_id_b = f"test-client-{uuid.uuid4()}"
    print(f"\n[A3] Listing sessions with different X-Client-Id B: {client_id_b}")
    resp = requests.get(
        f"{API_BASE}/chat/sessions",
        params={"mode": "ask-luca"},
        headers={"X-Client-Id": client_id_b},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    sessions_b = resp.json()
    session_ids_b = [s["id"] for s in sessions_b]
    assert session_id_a not in session_ids_b, f"Session {session_id_a} should NOT be in B's list (isolation failed)"
    print(f"✅ Isolation verified: A's session not visible to B")
    
    # Test 4: Try to access A's session with X-Client-Id B → 403
    print(f"\n[A4] Trying to access A's session with X-Client-Id B (should be 403)")
    resp = requests.get(
        f"{API_BASE}/chat/session/{session_id_a}",
        headers={"X-Client-Id": client_id_b},
        timeout=10
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    assert "Not your chat" in resp.text, f"Expected 'Not your chat' in response"
    print(f"✅ 403 'Not your chat' as expected")
    
    # Test 5: Access A's session with correct X-Client-Id A → 200
    print(f"\n[A5] Accessing A's session with correct X-Client-Id A (should be 200)")
    resp = requests.get(
        f"{API_BASE}/chat/session/{session_id_a}",
        headers={"X-Client-Id": client_id_a},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    session_data = resp.json()
    assert session_data["id"] == session_id_a
    assert "messages" in session_data
    assert len(session_data["messages"]) >= 2, "Should have at least 2 messages (user + assistant)"
    print(f"✅ Session retrieved successfully with {len(session_data['messages'])} messages")
    
    print("\n✅ SCENARIO A: All tests passed")
    return session_id_a, client_id_a


def test_scenario_b_logged_in_user_isolation():
    """
    B. Logged-in user isolation
    6. Register Alice, capture token
    7. POST /api/chat/stream with Alice's token, stone-guide mode
    8. GET /api/chat/sessions with Alice's token → contains session
    9. Register Bob, GET /api/chat/sessions with Bob's token → does NOT contain Alice's session
    10. GET /api/chat/session/{alice_session_id} with Bob's token → 403
    """
    print("\n### SCENARIO B: Logged-in user isolation")
    
    # Test 6: Register Alice
    alice_email = f"alice+chat{uuid.uuid4().hex[:8]}@example.com"
    print(f"\n[B6] Registering Alice: {alice_email}")
    resp = requests.post(
        f"{API_BASE}/auth/register",
        json={"fullName": "Alice", "email": alice_email, "password": "secret123"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    alice_data = resp.json()
    alice_token = alice_data["token"]
    print(f"✅ Alice registered, token: {alice_token[:20]}...")
    
    # Test 7: Create session with Alice's token
    print(f"\n[B7] Creating stone-guide session with Alice's token")
    resp = requests.post(
        f"{API_BASE}/chat/stream",
        json={"mode": "stone-guide", "message": "I need grounding."},
        headers={"Authorization": f"Bearer {alice_token}"},
        stream=True,
        timeout=30
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    
    alice_session_id, reply, chunks = consume_sse_stream(resp)
    assert alice_session_id, "Session ID not found"
    assert len(reply) > 30, f"Reply too short: {len(reply)} chars"
    print(f"✅ Alice's session created: {alice_session_id}")
    print(f"   Reply length: {len(reply)} chars")
    
    # Test 8: List sessions with Alice's token
    print(f"\n[B8] Listing stone-guide sessions with Alice's token")
    resp = requests.get(
        f"{API_BASE}/chat/sessions",
        params={"mode": "stone-guide"},
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    alice_sessions = resp.json()
    alice_session_ids = [s["id"] for s in alice_sessions]
    assert alice_session_id in alice_session_ids, f"Alice's session not found in her list"
    print(f"✅ Alice's session found in her list")
    
    # Test 9: Register Bob
    bob_email = f"bob+chat{uuid.uuid4().hex[:8]}@example.com"
    print(f"\n[B9] Registering Bob: {bob_email}")
    resp = requests.post(
        f"{API_BASE}/auth/register",
        json={"fullName": "Bob", "email": bob_email, "password": "secret456"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    bob_data = resp.json()
    bob_token = bob_data["token"]
    print(f"✅ Bob registered, token: {bob_token[:20]}...")
    
    # List sessions with Bob's token → should NOT contain Alice's session
    print(f"\n[B9 cont.] Listing stone-guide sessions with Bob's token")
    resp = requests.get(
        f"{API_BASE}/chat/sessions",
        params={"mode": "stone-guide"},
        headers={"Authorization": f"Bearer {bob_token}"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    bob_sessions = resp.json()
    bob_session_ids = [s["id"] for s in bob_sessions]
    assert alice_session_id not in bob_session_ids, f"Alice's session should NOT be in Bob's list"
    print(f"✅ Isolation verified: Alice's session not visible to Bob")
    
    # Test 10: Try to access Alice's session with Bob's token → 403
    print(f"\n[B10] Trying to access Alice's session with Bob's token (should be 403)")
    resp = requests.get(
        f"{API_BASE}/chat/session/{alice_session_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
        timeout=10
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    assert "Not your chat" in resp.text, f"Expected 'Not your chat' in response"
    print(f"✅ 403 'Not your chat' as expected")
    
    print("\n✅ SCENARIO B: All tests passed")
    return alice_session_id, alice_token, bob_token


def test_scenario_c_cross_principal_ownership(alice_session_id: str):
    """
    C. Cross-principal ownership on continuation
    11. Try continuing Alice's session with X-Client-Id (anon) → 403
    12. Continue with correct owner (Alice's token) → 200
    """
    print("\n### SCENARIO C: Cross-principal ownership on continuation")
    
    # Test 11: Try to continue Alice's session with anonymous X-Client-Id
    anon_client_id = f"test-client-{uuid.uuid4()}"
    print(f"\n[C11] Trying to continue Alice's session with X-Client-Id (should be 403)")
    resp = requests.post(
        f"{API_BASE}/chat/stream",
        json={"mode": "stone-guide", "sessionId": alice_session_id, "message": "Tell me more."},
        headers={"X-Client-Id": anon_client_id},
        stream=True,
        timeout=30
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    assert "This chat belongs to another account" in resp.text, f"Expected ownership error"
    print(f"✅ 403 'This chat belongs to another account' as expected")
    
    # Test 12: Continue with correct owner (Alice's token) → 200
    # We need Alice's token from scenario B
    print(f"\n[C12] Continuing Alice's session with correct token (should be 200)")
    # This test requires alice_token from scenario B, which we'll pass in
    print(f"⚠️  Skipping C12 - requires alice_token from scenario B (will test in integrated flow)")
    
    print("\n✅ SCENARIO C: Test 11 passed (Test 12 requires integrated flow)")


def test_scenario_c_continuation_with_token(alice_session_id: str, alice_token: str):
    """
    C12. Continue with correct owner (Alice's token) → 200
    """
    print(f"\n[C12] Continuing Alice's session with correct token")
    resp = requests.post(
        f"{API_BASE}/chat/stream",
        json={"mode": "stone-guide", "sessionId": alice_session_id, "message": "Tell me more about grounding."},
        headers={"Authorization": f"Bearer {alice_token}"},
        stream=True,
        timeout=30
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    session_id, reply, chunks = consume_sse_stream(resp)
    assert session_id == alice_session_id, f"Session ID mismatch"
    assert len(reply) > 30, f"Reply too short: {len(reply)} chars"
    print(f"✅ Continuation successful with {len(chunks)} chunks")


def test_scenario_d_rename_delete(alice_session_id: str, alice_token: str, bob_token: str):
    """
    D. Rename / delete
    13. PUT /api/chat/session/{alice_session_id} with Alice's token, rename → 200
    14. PUT rename with empty title → 400
    15. PUT rename by Bob (wrong owner) → 403
    16. DELETE by Bob → 403
    17. DELETE by Alice → 200, subsequent GET → 404
    """
    print("\n### SCENARIO D: Rename / delete")
    
    # Test 13: Rename with Alice's token
    print(f"\n[D13] Renaming Alice's session")
    resp = requests.put(
        f"{API_BASE}/chat/session/{alice_session_id}",
        json={"title": "My grounding chat"},
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("ok") is True
    assert data.get("title") == "My grounding chat"
    print(f"✅ Rename successful: {data['title']}")
    
    # Verify title persisted
    resp = requests.get(
        f"{API_BASE}/chat/session/{alice_session_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=10
    )
    assert resp.status_code == 200
    session_data = resp.json()
    assert session_data["title"] == "My grounding chat", "Title not persisted"
    print(f"✅ Title persisted correctly")
    
    # Test 14: Rename with empty title → 400
    print(f"\n[D14] Trying to rename with empty title (should be 400)")
    resp = requests.put(
        f"{API_BASE}/chat/session/{alice_session_id}",
        json={"title": ""},
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=10
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}"
    assert "Title cannot be empty" in resp.text or "empty" in resp.text.lower()
    print(f"✅ 400 for empty title as expected")
    
    # Test 15: Rename by Bob (wrong owner) → 403
    print(f"\n[D15] Trying to rename Alice's session with Bob's token (should be 403)")
    resp = requests.put(
        f"{API_BASE}/chat/session/{alice_session_id}",
        json={"title": "Bob's attempt"},
        headers={"Authorization": f"Bearer {bob_token}"},
        timeout=10
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    assert "Not your chat" in resp.text
    print(f"✅ 403 'Not your chat' as expected")
    
    # Test 16: DELETE by Bob → 403
    print(f"\n[D16] Trying to delete Alice's session with Bob's token (should be 403)")
    resp = requests.delete(
        f"{API_BASE}/chat/session/{alice_session_id}",
        headers={"Authorization": f"Bearer {bob_token}"},
        timeout=10
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"
    assert "Not your chat" in resp.text
    print(f"✅ 403 'Not your chat' as expected")
    
    # Test 17: DELETE by Alice → 200, then GET → 404
    print(f"\n[D17] Deleting Alice's session with Alice's token")
    resp = requests.delete(
        f"{API_BASE}/chat/session/{alice_session_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert data.get("ok") is True
    print(f"✅ Delete successful")
    
    # Verify session is gone
    print(f"\n[D17 cont.] Verifying session is deleted (should be 404)")
    resp = requests.get(
        f"{API_BASE}/chat/session/{alice_session_id}",
        headers={"Authorization": f"Bearer {alice_token}"},
        timeout=10
    )
    assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
    print(f"✅ 404 as expected - session deleted")
    
    print("\n✅ SCENARIO D: All tests passed")


def test_scenario_e_admin_writer_sessions():
    """
    E. Admin-writer sessions per admin
    18. Login as master admin, POST /api/chat/stream admin-writer mode
    19. GET /api/chat/sessions?mode=admin-writer with admin token → contains session
    20. Create separate admin writer2, login, GET sessions → must NOT contain master's session
    """
    print("\n### SCENARIO E: Admin-writer sessions per admin")
    
    # Test 18: Login as master admin
    print(f"\n[E18] Logging in as master admin")
    resp = requests.post(
        f"{API_BASE}/admin/login",
        json={"password": "1121211221"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    master_data = resp.json()
    master_token = master_data["token"]
    print(f"✅ Master admin logged in, token: {master_token[:20]}...")
    
    # Create admin-writer session
    print(f"\n[E18 cont.] Creating admin-writer session")
    resp = requests.post(
        f"{API_BASE}/chat/stream",
        json={"mode": "admin-writer", "message": "Draft a 1-sentence bracelet description"},
        headers={"Authorization": f"Bearer {master_token}"},
        stream=True,
        timeout=30
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    master_session_id, reply, chunks = consume_sse_stream(resp)
    assert master_session_id, "Session ID not found"
    assert len(reply) > 30, f"Reply too short: {len(reply)} chars"
    print(f"✅ Master admin session created: {master_session_id}")
    print(f"   Reply length: {len(reply)} chars")
    
    # Test 19: List admin-writer sessions with master token
    print(f"\n[E19] Listing admin-writer sessions with master token")
    resp = requests.get(
        f"{API_BASE}/chat/sessions",
        params={"mode": "admin-writer"},
        headers={"Authorization": f"Bearer {master_token}"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    master_sessions = resp.json()
    master_session_ids = [s["id"] for s in master_sessions]
    assert master_session_id in master_session_ids, f"Master's session not found in list"
    print(f"✅ Master's session found in list")
    
    # Test 20: Create separate admin writer2
    print(f"\n[E20] Creating separate admin writer2")
    resp = requests.post(
        f"{API_BASE}/admin/admins",
        json={"username": "writer2", "password": "pw2", "permissions": [], "isSuper": False},
        headers={"Authorization": f"Bearer {master_token}"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    print(f"✅ writer2 admin created")
    
    # Login as writer2
    print(f"\n[E20 cont.] Logging in as writer2")
    resp = requests.post(
        f"{API_BASE}/admin/login",
        json={"username": "writer2", "password": "pw2"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    writer2_data = resp.json()
    writer2_token = writer2_data["token"]
    print(f"✅ writer2 logged in, token: {writer2_token[:20]}...")
    
    # List sessions with writer2 token → should NOT contain master's session
    print(f"\n[E20 cont.] Listing admin-writer sessions with writer2 token")
    resp = requests.get(
        f"{API_BASE}/chat/sessions",
        params={"mode": "admin-writer"},
        headers={"Authorization": f"Bearer {writer2_token}"},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    writer2_sessions = resp.json()
    writer2_session_ids = [s["id"] for s in writer2_sessions]
    assert master_session_id not in writer2_session_ids, f"Master's session should NOT be in writer2's list"
    print(f"✅ Isolation verified: Master's session not visible to writer2")
    
    print("\n✅ SCENARIO E: All tests passed")


def test_scenario_f_title_auto_generation():
    """
    F. Title auto-generation
    21. Fresh POST /api/chat/stream with X-Client-Id, long message
        → session created, GET sessions → title should be non-empty (truncated to 60 chars + ellipsis)
    """
    print("\n### SCENARIO F: Title auto-generation")
    
    # Test 21: Create session with long message
    client_id = f"test-client-{uuid.uuid4()}"
    long_message = "How do I diffuse essential oils on a lava-stone bracelet?"
    print(f"\n[F21] Creating session with long message: '{long_message}'")
    
    resp = requests.post(
        f"{API_BASE}/chat/stream",
        json={"mode": "ask-luca", "message": long_message},
        headers={"X-Client-Id": client_id},
        stream=True,
        timeout=30
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    session_id, reply, chunks = consume_sse_stream(resp)
    assert session_id, "Session ID not found"
    print(f"✅ Session created: {session_id}")
    
    # List sessions and check title
    print(f"\n[F21 cont.] Checking auto-generated title")
    resp = requests.get(
        f"{API_BASE}/chat/sessions",
        headers={"X-Client-Id": client_id},
        timeout=10
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    sessions = resp.json()
    session_obj = next((s for s in sessions if s["id"] == session_id), None)
    assert session_obj, f"Session {session_id} not found in list"
    
    title = session_obj.get("title", "")
    assert title, "Title should be non-empty"
    # Title should be either the full message or truncated to 60 chars + ellipsis
    if len(long_message) > 60:
        assert len(title) <= 61, f"Title too long: {len(title)} chars (expected <= 61)"
        assert title.endswith("…") or title.endswith("..."), "Long title should end with ellipsis"
    else:
        assert long_message in title or title in long_message, f"Title should contain message text"
    
    print(f"✅ Title auto-generated correctly: '{title}'")
    print(f"   Original message length: {len(long_message)}, title length: {len(title)}")
    
    print("\n✅ SCENARIO F: All tests passed")


def test_scenario_g_regression_claude_replies():
    """
    G. Regression: chat still returns real replies with Claude
    22. POST /api/chat/stream ask-luca mode → no auth error, reply length > 30
    """
    print("\n### SCENARIO G: Regression - Claude replies working")
    
    # Test 22: Basic chat with ask-luca mode
    print(f"\n[G22] Testing basic chat with ask-luca mode (Claude integration)")
    resp = requests.post(
        f"{API_BASE}/chat/stream",
        json={"mode": "ask-luca", "message": "How do I care for the bracelet?"},
        stream=True,
        timeout=30
    )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    content_type = resp.headers.get("content-type", "")
    assert "text/event-stream" in content_type, f"Expected SSE content-type, got: {content_type}"
    
    session_id, reply, chunks = consume_sse_stream(resp)
    assert session_id, "Session ID not found"
    assert len(reply) > 30, f"Reply too short: {len(reply)} chars (expected > 30)"
    
    # Check for auth errors in reply
    error_keywords = ["AuthenticationError", "key not allowed", "OpenAIException", "permission denied", "invalid api key"]
    reply_lower = reply.lower()
    for keyword in error_keywords:
        assert keyword.lower() not in reply_lower, f"Found error keyword '{keyword}' in reply"
    
    print(f"✅ Chat working correctly with Claude")
    print(f"   Reply length: {len(reply)} chars, chunks: {len(chunks)}")
    print(f"   No authentication errors found")
    
    print("\n✅ SCENARIO G: All tests passed")


def main():
    """Run all test scenarios."""
    print("=" * 80)
    print("ESSENTIAL GEMSTONES - PER-USER CHAT MEMORY BACKEND TESTS")
    print("=" * 80)
    
    try:
        # Scenario A: Anonymous per-browser isolation
        session_id_a, client_id_a = test_scenario_a_anonymous_per_browser_isolation()
        
        # Scenario B: Logged-in user isolation
        alice_session_id, alice_token, bob_token = test_scenario_b_logged_in_user_isolation()
        
        # Scenario C: Cross-principal ownership on continuation
        test_scenario_c_cross_principal_ownership(alice_session_id)
        test_scenario_c_continuation_with_token(alice_session_id, alice_token)
        
        # Scenario D: Rename / delete
        test_scenario_d_rename_delete(alice_session_id, alice_token, bob_token)
        
        # Scenario E: Admin-writer sessions per admin
        test_scenario_e_admin_writer_sessions()
        
        # Scenario F: Title auto-generation
        test_scenario_f_title_auto_generation()
        
        # Scenario G: Regression - Claude replies
        test_scenario_g_regression_claude_replies()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
