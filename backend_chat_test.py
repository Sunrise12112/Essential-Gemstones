#!/usr/bin/env python3
"""
Comprehensive backend test suite for Essential Gemstones Gemini chat endpoints.
Tests SSE streaming chat with three modes: ask-luca, stone-guide, admin-writer.
"""
import json
import sys
import time
import uuid
from typing import Optional, Tuple

import requests

# Configuration
BASE_URL = "https://gemstone-makeover.preview.emergentagent.com/api"
MASTER_PASSWORD = "1121211221"

# Global state
master_token = None
user_token = None
ask_luca_session_id = None
stone_guide_session_id = None


def log_test(scenario: str, test: str, status: str, details: str = ""):
    """Log test results in a structured format."""
    symbol = "✅" if status == "PASS" else "❌"
    print(f"{symbol} [{scenario}] {test}")
    if details:
        # Indent multi-line details
        for line in details.split('\n'):
            print(f"   {line}")


def parse_sse_stream(response) -> Tuple[Optional[str], str, bool, Optional[str]]:
    """
    Parse SSE stream from response.
    Returns: (session_id, concatenated_text, got_done_event, error_message)
    """
    session_id = None
    text_chunks = []
    got_done = False
    error_msg = None
    
    try:
        for line in response.iter_lines(decode_unicode=True):
            if not line or line.strip() == "":
                continue
            
            # Parse SSE format: "event: name" or "data: content"
            if line.startswith("event:"):
                event_type = line.split(":", 1)[1].strip()
                if event_type == "session":
                    # Next line should be data with session ID
                    continue
                elif event_type == "done":
                    got_done = True
                elif event_type == "error":
                    # Next line should be data with error message
                    continue
            elif line.startswith("data:"):
                data = line.split(":", 1)[1].strip()
                
                # Check if this is session ID (UUID format)
                if session_id is None and len(data) == 36 and data.count('-') == 4:
                    session_id = data
                # Check if this is error message (after error event)
                elif error_msg is None and any(err in data.lower() for err in ['error', 'failed', 'exception']):
                    error_msg = data
                # Otherwise it's a text chunk
                else:
                    # Unescape newlines that were escaped in SSE
                    chunk = data.replace("\\n", "\n")
                    text_chunks.append(chunk)
    except Exception as e:
        error_msg = f"Stream parsing error: {str(e)}"
    
    full_text = "".join(text_chunks)
    return session_id, full_text, got_done, error_msg


def test_a_ask_luca_mode():
    """Test scenario A: ask-luca mode (public, no auth)."""
    global ask_luca_session_id
    
    print("\n" + "="*80)
    print("SCENARIO A: ASK-LUCA MODE (PUBLIC, NO AUTH)")
    print("="*80)
    
    # A1: First message - bracelet care
    print("\n[A1] Testing first message about bracelet care...")
    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "mode": "ask-luca",
            "message": "How do I care for my lava stone bracelet?"
        },
        stream=True,
        timeout=60
    )
    
    if resp.status_code == 200:
        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            session_id, reply_text, got_done, error = parse_sse_stream(resp)
            
            if session_id and reply_text and got_done:
                ask_luca_session_id = session_id
                # Check if reply mentions lava stone care
                reply_lower = reply_text.lower()
                mentions_care = any(word in reply_lower for word in ['clean', 'water', 'chemical', 'care', 'wipe', 'avoid'])
                
                if mentions_care and len(reply_text) > 20:
                    log_test("A1", "First message returns SSE stream with session, text, and done", "PASS",
                            f"Session ID: {session_id}\nReply excerpt: {reply_text[:200]}...")
                else:
                    log_test("A1", "First message returns SSE stream with session, text, and done", "FAIL",
                            f"Reply doesn't mention care or is too short: {reply_text[:200]}")
            else:
                log_test("A1", "First message returns SSE stream with session, text, and done", "FAIL",
                        f"Missing components - Session: {session_id}, Text length: {len(reply_text)}, Done: {got_done}, Error: {error}")
        else:
            log_test("A1", "First message returns SSE stream with session, text, and done", "FAIL",
                    f"Wrong content-type: {content_type}")
    else:
        log_test("A1", "First message returns SSE stream with session, text, and done", "FAIL",
                f"Status: {resp.status_code}, Body: {resp.text[:200]}")
    
    # A2: Follow-up message with same session
    if ask_luca_session_id:
        print("\n[A2] Testing follow-up message with same session...")
        resp = requests.post(
            f"{BASE_URL}/chat/stream",
            json={
                "mode": "ask-luca",
                "sessionId": ask_luca_session_id,
                "message": "And how about essential oils?"
            },
            stream=True,
            timeout=60
        )
        
        if resp.status_code == 200:
            session_id, reply_text, got_done, error = parse_sse_stream(resp)
            
            if session_id == ask_luca_session_id and reply_text and got_done:
                # Check if reply mentions oils or porous lava
                reply_lower = reply_text.lower()
                mentions_oils = any(word in reply_lower for word in ['oil', 'porous', 'lava', 'absorb', 'diffuse'])
                
                if mentions_oils:
                    log_test("A2", "Follow-up message maintains context", "PASS",
                            f"Reply excerpt: {reply_text[:200]}...")
                else:
                    log_test("A2", "Follow-up message maintains context", "FAIL",
                            f"Reply doesn't mention oils/porous: {reply_text[:200]}")
            else:
                log_test("A2", "Follow-up message maintains context", "FAIL",
                        f"Session mismatch or missing data - Expected: {ask_luca_session_id}, Got: {session_id}")
        else:
            log_test("A2", "Follow-up message maintains context", "FAIL",
                    f"Status: {resp.status_code}")
    else:
        log_test("A2", "Follow-up message maintains context", "FAIL",
                "No session ID from A1")
    
    # A3: Get session history
    if ask_luca_session_id:
        print("\n[A3] Testing session history retrieval...")
        resp = requests.get(f"{BASE_URL}/chat/session/{ask_luca_session_id}")
        
        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("messages", [])
            mode = data.get("mode")
            
            if mode == "ask-luca" and len(messages) >= 4:
                user_msgs = [m for m in messages if m.get("role") == "user"]
                assistant_msgs = [m for m in messages if m.get("role") == "assistant"]
                
                if len(user_msgs) >= 2 and len(assistant_msgs) >= 2:
                    log_test("A3", "GET session returns conversation history", "PASS",
                            f"Mode: {mode}, Total messages: {len(messages)} (2 user + 2 assistant)")
                else:
                    log_test("A3", "GET session returns conversation history", "FAIL",
                            f"Wrong message counts - User: {len(user_msgs)}, Assistant: {len(assistant_msgs)}")
            else:
                log_test("A3", "GET session returns conversation history", "FAIL",
                        f"Mode: {mode}, Message count: {len(messages)} (expected >= 4)")
        else:
            log_test("A3", "GET session returns conversation history", "FAIL",
                    f"Status: {resp.status_code}")
    else:
        log_test("A3", "GET session returns conversation history", "FAIL",
                "No session ID from A1")
    
    # A4: Empty message validation
    print("\n[A4] Testing empty message validation...")
    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "mode": "ask-luca",
            "message": ""
        },
        stream=True,
        timeout=10
    )
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "empty" in detail.lower():
            log_test("A4", "Empty message returns 400", "PASS", f"Detail: {detail}")
        else:
            log_test("A4", "Empty message returns 400", "FAIL", f"Wrong detail: {detail}")
    else:
        log_test("A4", "Empty message returns 400", "FAIL", f"Status: {resp.status_code}")
    
    # A5: Unknown mode validation
    print("\n[A5] Testing unknown mode validation...")
    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "mode": "unknown-mode",
            "message": "hi"
        },
        stream=True,
        timeout=10
    )
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "unknown" in detail.lower() or "mode" in detail.lower():
            log_test("A5", "Unknown mode returns 400", "PASS", f"Detail: {detail}")
        else:
            log_test("A5", "Unknown mode returns 400", "FAIL", f"Wrong detail: {detail}")
    else:
        log_test("A5", "Unknown mode returns 400", "FAIL", f"Status: {resp.status_code}")
    
    # A6: Message too long validation
    print("\n[A6] Testing message length validation...")
    long_message = "x" * 4001
    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "mode": "ask-luca",
            "message": long_message
        },
        stream=True,
        timeout=10
    )
    
    if resp.status_code == 400:
        detail = resp.json().get("detail", "")
        if "too long" in detail.lower() or "message" in detail.lower():
            log_test("A6", "Message >4000 chars returns 400", "PASS", f"Detail: {detail}")
        else:
            log_test("A6", "Message >4000 chars returns 400", "FAIL", f"Wrong detail: {detail}")
    else:
        log_test("A6", "Message >4000 chars returns 400", "FAIL", f"Status: {resp.status_code}")


def test_b_stone_guide_mode():
    """Test scenario B: stone-guide mode (public, no auth)."""
    global stone_guide_session_id
    
    print("\n" + "="*80)
    print("SCENARIO B: STONE-GUIDE MODE (PUBLIC, NO AUTH)")
    print("="*80)
    
    # B1: First message about grounding
    print("\n[B1] Testing stone recommendation for grounding...")
    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "mode": "stone-guide",
            "message": "I need help feeling more grounded and calm."
        },
        stream=True,
        timeout=60
    )
    
    if resp.status_code == 200:
        session_id, reply_text, got_done, error = parse_sse_stream(resp)
        
        if session_id and reply_text and got_done:
            stone_guide_session_id = session_id
            # Check if reply mentions a stone or asks clarifying question
            reply_lower = reply_text.lower()
            mentions_stone = any(word in reply_lower for word in ['jasper', 'stone', 'grounding', 'chakra', 'red'])
            asks_question = '?' in reply_text
            
            if mentions_stone or asks_question:
                log_test("B1", "Stone-guide provides recommendation or asks question", "PASS",
                        f"Session ID: {session_id}\nReply excerpt: {reply_text[:200]}...")
            else:
                log_test("B1", "Stone-guide provides recommendation or asks question", "FAIL",
                        f"Reply doesn't mention stones or ask questions: {reply_text[:200]}")
        else:
            log_test("B1", "Stone-guide provides recommendation or asks question", "FAIL",
                    f"Missing components - Session: {session_id}, Text length: {len(reply_text)}, Done: {got_done}")
    else:
        log_test("B1", "Stone-guide provides recommendation or asks question", "FAIL",
                f"Status: {resp.status_code}")
    
    # B2: Cross-mode session reuse guard
    if ask_luca_session_id:
        print("\n[B2] Testing cross-mode session reuse prevention...")
        resp = requests.post(
            f"{BASE_URL}/chat/stream",
            json={
                "mode": "stone-guide",
                "sessionId": ask_luca_session_id,  # Using ask-luca session with stone-guide mode
                "message": "What stone should I use?"
            },
            stream=True,
            timeout=10
        )
        
        if resp.status_code == 400:
            detail = resp.json().get("detail", "")
            if "mismatch" in detail.lower() or "mode" in detail.lower():
                log_test("B2", "Cross-mode session reuse returns 400", "PASS", f"Detail: {detail}")
            else:
                log_test("B2", "Cross-mode session reuse returns 400", "FAIL", f"Wrong detail: {detail}")
        else:
            log_test("B2", "Cross-mode session reuse returns 400", "FAIL", f"Status: {resp.status_code}")
    else:
        log_test("B2", "Cross-mode session reuse returns 400", "FAIL",
                "No ask-luca session ID from scenario A")


def test_c_admin_writer_mode():
    """Test scenario C: admin-writer mode (admin auth required)."""
    global master_token, user_token
    
    print("\n" + "="*80)
    print("SCENARIO C: ADMIN-WRITER MODE (ADMIN AUTH REQUIRED)")
    print("="*80)
    
    # C1: Without auth header
    print("\n[C1] Testing admin-writer without auth...")
    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "mode": "admin-writer",
            "message": "Write a 1-sentence description for a lava-stone bracelet with amethyst."
        },
        stream=True,
        timeout=10
    )
    
    if resp.status_code == 401:
        detail = resp.json().get("detail", "")
        if "admin" in detail.lower() or "auth" in detail.lower():
            log_test("C1", "Admin-writer without auth returns 401", "PASS", f"Detail: {detail}")
        else:
            log_test("C1", "Admin-writer without auth returns 401", "FAIL", f"Wrong detail: {detail}")
    else:
        log_test("C1", "Admin-writer without auth returns 401", "FAIL", f"Status: {resp.status_code}")
    
    # C2: Get master admin token
    print("\n[C2] Getting master admin token...")
    resp = requests.post(f"{BASE_URL}/admin/login", json={"password": MASTER_PASSWORD})
    
    if resp.status_code == 200:
        master_token = resp.json()["token"]
        log_test("C2", "Master admin login successful", "PASS", f"Token length: {len(master_token)}")
    else:
        log_test("C2", "Master admin login successful", "FAIL", f"Status: {resp.status_code}")
        return
    
    # C3: With admin token
    print("\n[C3] Testing admin-writer with admin token...")
    resp = requests.post(
        f"{BASE_URL}/chat/stream",
        json={
            "mode": "admin-writer",
            "message": "Write a 1-sentence description for a lava-stone bracelet with amethyst."
        },
        headers={"Authorization": f"Bearer {master_token}"},
        stream=True,
        timeout=60
    )
    
    if resp.status_code == 200:
        session_id, reply_text, got_done, error = parse_sse_stream(resp)
        
        if session_id and reply_text and got_done:
            # Check if reply contains actual content (not just acknowledgment)
            if len(reply_text) > 30:
                log_test("C3", "Admin-writer with admin token returns content", "PASS",
                        f"Reply excerpt: {reply_text[:200]}...")
            else:
                log_test("C3", "Admin-writer with admin token returns content", "FAIL",
                        f"Reply too short: {reply_text}")
        else:
            log_test("C3", "Admin-writer with admin token returns content", "FAIL",
                    f"Missing components - Session: {session_id}, Text length: {len(reply_text)}, Done: {got_done}")
    else:
        log_test("C3", "Admin-writer with admin token returns content", "FAIL",
                f"Status: {resp.status_code}")
    
    # C4: With user token (should fail)
    print("\n[C4] Testing admin-writer with user token...")
    # First create a user
    test_email = f"chattest{int(time.time())}@example.com"
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "fullName": "Chat Test User",
        "email": test_email,
        "password": "testpass123",
        "subscribeNewsletter": False
    })
    
    if resp.status_code == 200:
        user_token = resp.json()["token"]
        
        # Try admin-writer with user token
        resp = requests.post(
            f"{BASE_URL}/chat/stream",
            json={
                "mode": "admin-writer",
                "message": "Write something"
            },
            headers={"Authorization": f"Bearer {user_token}"},
            stream=True,
            timeout=10
        )
        
        if resp.status_code == 403:
            detail = resp.json().get("detail", "")
            if "admin" in detail.lower():
                log_test("C4", "Admin-writer with user token returns 403", "PASS", f"Detail: {detail}")
            else:
                log_test("C4", "Admin-writer with user token returns 403", "FAIL", f"Wrong detail: {detail}")
        else:
            log_test("C4", "Admin-writer with user token returns 403", "FAIL", f"Status: {resp.status_code}")
    else:
        log_test("C4", "Admin-writer with user token returns 403", "FAIL",
                f"Cannot create test user: {resp.status_code}")


def test_d_admin_session_management():
    """Test scenario D: Admin session management."""
    print("\n" + "="*80)
    print("SCENARIO D: ADMIN SESSION MANAGEMENT")
    print("="*80)
    
    if not master_token:
        log_test("D1-D4", "Admin session management", "FAIL",
                "No master token available")
        return
    
    # D1: List chat sessions with master token
    print("\n[D1] Testing GET /admin/chat-sessions with master token...")
    resp = requests.get(
        f"{BASE_URL}/admin/chat-sessions",
        headers={"Authorization": f"Bearer {master_token}"}
    )
    
    if resp.status_code == 200:
        sessions = resp.json()
        if isinstance(sessions, list):
            # Check if our test sessions are in the list
            session_ids = [s.get("id") for s in sessions]
            has_ask_luca = ask_luca_session_id in session_ids if ask_luca_session_id else False
            has_stone_guide = stone_guide_session_id in session_ids if stone_guide_session_id else False
            
            # Verify session structure
            if sessions:
                sample = sessions[0]
                required_fields = ["id", "mode", "createdAt", "messageCount"]
                has_all_fields = all(f in sample for f in required_fields)
                
                if has_all_fields:
                    log_test("D1", "GET /admin/chat-sessions returns session list", "PASS",
                            f"Total sessions: {len(sessions)}, Has ask-luca: {has_ask_luca}, Has stone-guide: {has_stone_guide}")
                else:
                    log_test("D1", "GET /admin/chat-sessions returns session list", "FAIL",
                            f"Missing fields in session: {sample}")
            else:
                log_test("D1", "GET /admin/chat-sessions returns session list", "PASS",
                        "No sessions yet (empty list is valid)")
        else:
            log_test("D1", "GET /admin/chat-sessions returns session list", "FAIL",
                    f"Response is not a list: {type(sessions)}")
    else:
        log_test("D1", "GET /admin/chat-sessions returns session list", "FAIL",
                f"Status: {resp.status_code}")
    
    # D2: Without token
    print("\n[D2] Testing GET /admin/chat-sessions without token...")
    resp = requests.get(f"{BASE_URL}/admin/chat-sessions")
    
    if resp.status_code == 401:
        log_test("D2", "GET /admin/chat-sessions without token returns 401", "PASS")
    else:
        log_test("D2", "GET /admin/chat-sessions without token returns 401", "FAIL",
                f"Status: {resp.status_code}")
    
    # D3: Delete a session
    if ask_luca_session_id:
        print("\n[D3] Testing DELETE /admin/chat-sessions/{id}...")
        resp = requests.delete(
            f"{BASE_URL}/admin/chat-sessions/{ask_luca_session_id}",
            headers={"Authorization": f"Bearer {master_token}"}
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok") == True:
                # Verify session is actually deleted
                resp2 = requests.get(f"{BASE_URL}/chat/session/{ask_luca_session_id}")
                if resp2.status_code == 404:
                    log_test("D3", "DELETE session works and session is gone", "PASS")
                else:
                    log_test("D3", "DELETE session works and session is gone", "FAIL",
                            f"Session still accessible: {resp2.status_code}")
            else:
                log_test("D3", "DELETE session works and session is gone", "FAIL",
                        f"Response: {data}")
        else:
            log_test("D3", "DELETE session works and session is gone", "FAIL",
                    f"Status: {resp.status_code}")
    else:
        log_test("D3", "DELETE session works and session is gone", "FAIL",
                "No ask-luca session ID available")
    
    # D4: Delete non-existent session
    print("\n[D4] Testing DELETE non-existent session...")
    fake_id = str(uuid.uuid4())
    resp = requests.delete(
        f"{BASE_URL}/admin/chat-sessions/{fake_id}",
        headers={"Authorization": f"Bearer {master_token}"}
    )
    
    if resp.status_code == 404:
        log_test("D4", "DELETE non-existent session returns 404", "PASS")
    else:
        log_test("D4", "DELETE non-existent session returns 404", "FAIL",
                f"Status: {resp.status_code}")


def main():
    """Run all test scenarios."""
    print("\n" + "="*80)
    print("ESSENTIAL GEMSTONES GEMINI CHAT ENDPOINTS TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Testing SSE streaming with emergentintegrations + Gemini")
    
    try:
        test_a_ask_luca_mode()
        test_b_stone_guide_mode()
        test_c_admin_writer_mode()
        test_d_admin_session_management()
        
        print("\n" + "="*80)
        print("TEST SUITE COMPLETE")
        print("="*80)
        print("\nNOTE: If Gemini API calls fail due to network/rate limits,")
        print("the endpoint should emit 'event: error' with error details.")
        print("This is expected behavior and not a test failure.")
        
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
