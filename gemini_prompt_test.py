#!/usr/bin/env python3
"""
Gemini Chat Prompt Verification Test Suite
Tests the AI system prompts to ensure:
1. Luca is referred to with he/him/his pronouns (NEVER she/her/they)
2. No age-forward descriptors (NEVER "nine-year-old", "young founder", "kid founder", etc.)

Each test is run TWICE to account for LLM non-determinism.
"""
import asyncio
import json
import re
import sys
from typing import List, Dict, Any, Optional

import httpx

# Configuration
BASE_URL = "https://gemstone-makeover.preview.emergentagent.com/api"
MASTER_PASSWORD = "1121211221"

# Test results storage
test_results: List[Dict[str, Any]] = []


def log_section(title: str):
    """Print a section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def log_test(test_name: str, run: int, status: str, details: str = ""):
    """Log test results."""
    symbol = "✅" if status == "PASS" else "❌"
    print(f"{symbol} {test_name} (Run {run}): {status}")
    if details:
        for line in details.split("\n"):
            print(f"   {line}")


async def stream_chat(
    mode: str,
    message: str,
    session_id: Optional[str] = None,
    admin_token: Optional[str] = None
) -> tuple[str, str]:
    """
    Stream a chat message and return (full_reply, session_id).
    
    Args:
        mode: Chat mode (ask-luca, stone-guide, admin-writer)
        message: User message
        session_id: Optional session ID for context
        admin_token: Optional admin token for admin-writer mode
    
    Returns:
        Tuple of (full_reply_text, session_id)
    """
    url = f"{BASE_URL}/chat/stream"
    payload = {
        "mode": mode,
        "message": message
    }
    if session_id:
        payload["sessionId"] = session_id
    
    headers = {}
    if admin_token:
        headers["Authorization"] = f"Bearer {admin_token}"
    
    full_reply = ""
    returned_session_id = session_id or ""
    waiting_for_session_id = False
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise Exception(f"HTTP {response.status_code}: {error_text.decode()}")
            
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith("event: session"):
                    waiting_for_session_id = True
                elif line.startswith("data: "):
                    chunk = line[6:]  # Remove "data: " prefix
                    
                    # If we're waiting for session ID, this is it
                    if waiting_for_session_id:
                        returned_session_id = chunk
                        waiting_for_session_id = False
                    else:
                        # This is actual reply content
                        # Unescape newlines that were escaped in SSE
                        chunk = chunk.replace("\\n", "\n")
                        full_reply += chunk
                elif line.startswith("event: done"):
                    break
                elif line.startswith("event: error"):
                    continue
    
    return full_reply.strip(), returned_session_id


def check_pronouns(text: str, test_name: str) -> Dict[str, Any]:
    """
    Check pronoun usage in the text.
    
    Returns dict with:
        - has_correct_pronouns: bool (has he/him/his)
        - has_forbidden_pronouns: bool (has she/her/they as pronouns)
        - forbidden_matches: list of forbidden pronoun matches
        - correct_matches: list of correct pronoun matches
    """
    text_lower = text.lower()
    
    # Check for correct pronouns (he/him/his)
    correct_patterns = [
        r'\bhe\b', r'\bhim\b', r'\bhis\b',
        r'\bhe\'s\b', r'\bhe\'ll\b', r'\bhe\'d\b'
    ]
    correct_matches = []
    for pattern in correct_patterns:
        matches = re.findall(pattern, text_lower)
        correct_matches.extend(matches)
    
    has_correct_pronouns = len(correct_matches) > 0
    
    # Check for forbidden pronouns (she/her/they as pronouns for Luca)
    # We need to be careful with "they" as it might be used for other contexts
    forbidden_patterns = [
        r'\bshe\b', r'\bher\b', r'\bhers\b', r'\bherself\b',
        r'\bshe\'s\b', r'\bshe\'ll\b', r'\bshe\'d\b'
    ]
    forbidden_matches = []
    for pattern in forbidden_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            forbidden_matches.extend(matches)
    
    # Special check for "they/them" used as Luca's pronoun
    # Look for patterns like "they founded", "they created", "them as founder"
    they_them_patterns = [
        r'\bthey\s+(?:founded|created|started|made|designed|built)\b',
        r'\bthem\s+as\s+(?:founder|creator|entrepreneur)\b',
        r'\btheir\s+(?:brand|business|company|bracelets)\b'
    ]
    for pattern in they_them_patterns:
        matches = re.findall(pattern, text_lower)
        if matches:
            forbidden_matches.extend([f"they/them (as pronoun): {m}" for m in matches])
    
    has_forbidden_pronouns = len(forbidden_matches) > 0
    
    return {
        "has_correct_pronouns": has_correct_pronouns,
        "has_forbidden_pronouns": has_forbidden_pronouns,
        "forbidden_matches": forbidden_matches,
        "correct_matches": correct_matches
    }


def check_age_descriptors(text: str) -> Dict[str, Any]:
    """
    Check for forbidden age-forward descriptors.
    
    Returns dict with:
        - has_age_descriptors: bool
        - matches: list of matched age descriptors
    """
    text_lower = text.lower()
    
    # Forbidden age descriptors
    forbidden_phrases = [
        r'\bnine-year-old\b', r'\b9-year-old\b', r'\b9 year old\b',
        r'\byoung founder\b', r'\bkid founder\b', r'\byoung boy\b',
        r'\blittle boy\b', r'\bchild founder\b', r'\byoung entrepreneur\b',
        r'\bkid entrepreneur\b', r'\b9 years old\b', r'\bnine years old\b'
    ]
    
    matches = []
    for pattern in forbidden_phrases:
        found = re.findall(pattern, text_lower)
        if found:
            matches.extend(found)
    
    return {
        "has_age_descriptors": len(matches) > 0,
        "matches": matches
    }


async def run_test(
    test_name: str,
    mode: str,
    message: str,
    admin_token: Optional[str] = None,
    check_age: bool = True,
    check_pronouns_required: bool = True,
    allow_age_mention: bool = False
) -> Dict[str, Any]:
    """
    Run a single test twice and return results.
    
    Args:
        test_name: Name of the test
        mode: Chat mode
        message: User message
        admin_token: Optional admin token
        check_age: Whether to check for age descriptors
        check_pronouns_required: Whether pronouns are required
        allow_age_mention: Whether age mentions are allowed (for direct age questions)
    """
    log_section(f"TEST: {test_name}")
    
    results = {
        "test_name": test_name,
        "mode": mode,
        "message": message,
        "runs": []
    }
    
    # Run the test twice
    for run in [1, 2]:
        print(f"\n--- Run {run} ---")
        
        try:
            # Stream the chat
            reply, session_id = await stream_chat(mode, message, admin_token=admin_token)
            
            # Show first 500 chars of reply
            reply_preview = reply[:500] + "..." if len(reply) > 500 else reply
            print(f"Reply ({len(reply)} chars):\n{reply_preview}\n")
            
            # Check pronouns
            pronoun_check = check_pronouns(reply, test_name)
            
            # Check age descriptors
            age_check = check_age_descriptors(reply)
            
            # Determine pass/fail
            passed = True
            issues = []
            
            if check_pronouns_required:
                if pronoun_check["has_forbidden_pronouns"]:
                    passed = False
                    issues.append(f"FORBIDDEN PRONOUNS FOUND: {pronoun_check['forbidden_matches']}")
                
                if not pronoun_check["has_correct_pronouns"] and "luca" in reply.lower():
                    # Only require correct pronouns if Luca is mentioned
                    issues.append(f"WARNING: Luca mentioned but no he/him/his pronouns found")
            
            if check_age and not allow_age_mention:
                if age_check["has_age_descriptors"]:
                    passed = False
                    issues.append(f"AGE DESCRIPTORS FOUND: {age_check['matches']}")
            
            # Log result
            status = "PASS" if passed else "FAIL"
            details = "\n".join(issues) if issues else "All checks passed"
            log_test(test_name, run, status, details)
            
            # Store result
            run_result = {
                "run": run,
                "reply": reply,
                "reply_length": len(reply),
                "session_id": session_id,
                "pronoun_check": pronoun_check,
                "age_check": age_check,
                "passed": passed,
                "issues": issues
            }
            results["runs"].append(run_result)
            
        except Exception as e:
            log_test(test_name, run, "ERROR", str(e))
            results["runs"].append({
                "run": run,
                "error": str(e),
                "passed": False
            })
    
    # Overall result: pass if both runs passed
    results["overall_passed"] = all(r.get("passed", False) for r in results["runs"])
    
    return results


async def get_admin_token() -> str:
    """Get admin token by logging in."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/admin/login",
            json={"password": MASTER_PASSWORD}
        )
        if resp.status_code != 200:
            raise Exception(f"Admin login failed: {resp.status_code} {resp.text}")
        data = resp.json()
        return data["token"]


async def main():
    """Run all tests."""
    print("=" * 80)
    print("GEMINI CHAT PROMPT VERIFICATION TEST SUITE")
    print("=" * 80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Testing pronoun correctness and age descriptor removal")
    print("Each test runs TWICE to account for LLM non-determinism")
    
    all_results = []
    
    # Test 1: Pronoun correctness (ask-luca)
    result1 = await run_test(
        test_name="Test 1: Pronoun correctness (ask-luca)",
        mode="ask-luca",
        message="Tell me about who founded this brand and what they're like.",
        check_age=True,
        check_pronouns_required=True
    )
    all_results.append(result1)
    
    # Test 2: No age qualifiers (ask-luca)
    result2 = await run_test(
        test_name="Test 2: No age qualifiers (ask-luca)",
        mode="ask-luca",
        message="Who makes these bracelets?",
        check_age=True,
        check_pronouns_required=True
    )
    all_results.append(result2)
    
    # Test 3: Age question is OK to answer (ask-luca)
    result3 = await run_test(
        test_name="Test 3: Age question is OK to answer (ask-luca)",
        mode="ask-luca",
        message="How old is Luca?",
        check_age=False,  # Age mentions are OK here
        check_pronouns_required=True,
        allow_age_mention=True
    )
    all_results.append(result3)
    
    # Test 4: Pronouns in stone-guide
    result4 = await run_test(
        test_name="Test 4: Pronouns in stone-guide",
        mode="stone-guide",
        message="Who designed the chakra bracelet? What's their story?",
        check_age=True,
        check_pronouns_required=True
    )
    all_results.append(result4)
    
    # Test 5: Admin-writer pronoun (admin auth required)
    print("\n" + "=" * 80)
    print("Getting admin token for Test 5...")
    print("=" * 80)
    try:
        admin_token = await get_admin_token()
        print(f"✅ Admin token obtained (length: {len(admin_token)})")
        
        result5 = await run_test(
            test_name="Test 5: Admin-writer pronoun (admin auth)",
            mode="admin-writer",
            message="Write a 2-sentence bio blurb about our founder Luca.",
            admin_token=admin_token,
            check_age=True,
            check_pronouns_required=True
        )
        all_results.append(result5)
    except Exception as e:
        print(f"❌ Failed to get admin token: {e}")
        all_results.append({
            "test_name": "Test 5: Admin-writer pronoun (admin auth)",
            "error": str(e),
            "overall_passed": False
        })
    
    # Print summary
    log_section("TEST SUMMARY")
    
    total_tests = len(all_results)
    passed_tests = sum(1 for r in all_results if r.get("overall_passed", False))
    failed_tests = total_tests - passed_tests
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print()
    
    for result in all_results:
        test_name = result["test_name"]
        passed = result.get("overall_passed", False)
        symbol = "✅" if passed else "❌"
        print(f"{symbol} {test_name}")
        
        if not passed and "runs" in result:
            for run_result in result["runs"]:
                if not run_result.get("passed", False):
                    issues = run_result.get("issues", [])
                    for issue in issues:
                        print(f"   - {issue}")
    
    # Detailed report
    log_section("DETAILED REPORT")
    
    for result in all_results:
        print(f"\n{result['test_name']}")
        print("-" * 80)
        
        if "error" in result:
            print(f"ERROR: {result['error']}")
            continue
        
        for run_result in result.get("runs", []):
            run = run_result.get("run", 0)
            print(f"\nRun {run}:")
            
            if "error" in run_result:
                print(f"  ERROR: {run_result['error']}")
                continue
            
            reply = run_result.get("reply", "")
            reply_preview = reply[:500] + "..." if len(reply) > 500 else reply
            print(f"  Reply ({len(reply)} chars): {reply_preview}")
            
            pronoun_check = run_result.get("pronoun_check", {})
            print(f"  Correct pronouns (he/him/his): {pronoun_check.get('has_correct_pronouns', False)}")
            if pronoun_check.get("correct_matches"):
                print(f"    Matches: {pronoun_check['correct_matches'][:5]}")  # Show first 5
            print(f"  Forbidden pronouns (she/her/they): {pronoun_check.get('has_forbidden_pronouns', False)}")
            if pronoun_check.get("forbidden_matches"):
                print(f"    Matches: {pronoun_check['forbidden_matches']}")
            
            age_check = run_result.get("age_check", {})
            print(f"  Age descriptors: {age_check.get('has_age_descriptors', False)}")
            if age_check.get("matches"):
                print(f"    Matches: {age_check['matches']}")
            
            print(f"  Status: {'PASS' if run_result.get('passed', False) else 'FAIL'}")
    
    # Exit with appropriate code
    if failed_tests > 0:
        print(f"\n❌ {failed_tests} test(s) failed")
        sys.exit(1)
    else:
        print(f"\n✅ All {total_tests} tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
