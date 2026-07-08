#!/usr/bin/env python3
"""
Additional smoke tests for Gemini chat SSE streaming.
Verifies:
- SSE format (event: session, data: chunks, event: done)
- Meaningful text is returned (length > 30 chars)
- Session ID is returned
"""
import asyncio
import httpx

BASE_URL = "https://gemstone-makeover.preview.emergentagent.com/api"


async def test_sse_format():
    """Test that SSE format is correct."""
    print("=" * 80)
    print("SMOKE TEST: SSE Format Verification")
    print("=" * 80)
    
    url = f"{BASE_URL}/chat/stream"
    payload = {
        "mode": "ask-luca",
        "message": "What stones do you use?"
    }
    
    has_session_event = False
    has_data_chunks = False
    has_done_event = False
    session_id = None
    full_reply = ""
    data_chunk_count = 0
    waiting_for_session_id = False
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            print(f"Response status: {response.status_code}")
            print(f"Content-Type: {response.headers.get('content-type')}")
            
            if response.status_code != 200:
                print(f"❌ FAIL: Expected 200, got {response.status_code}")
                return False
            
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('text/event-stream'):
                print(f"❌ FAIL: Expected text/event-stream, got {content_type}")
                return False
            
            print("\nSSE Stream:")
            print("-" * 80)
            
            async for line in response.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                
                # Print first 100 chars of each line
                print(line[:100] + ("..." if len(line) > 100 else ""))
                
                if line.startswith("event: session"):
                    has_session_event = True
                    waiting_for_session_id = True
                elif line.startswith("data: "):
                    chunk = line[6:]
                    
                    # If we're waiting for session ID, this is it
                    if waiting_for_session_id:
                        session_id = chunk
                        waiting_for_session_id = False
                    else:
                        # This is actual reply content
                        has_data_chunks = True
                        data_chunk_count += 1
                        chunk = chunk.replace("\\n", "\n")
                        full_reply += chunk
                elif line.startswith("event: done"):
                    has_done_event = True
                    break
    
    print("-" * 80)
    print(f"\nSession ID: {session_id}")
    print(f"Data chunks received: {data_chunk_count}")
    print(f"Full reply length: {len(full_reply)} chars")
    print(f"Full reply: {full_reply[:200]}{'...' if len(full_reply) > 200 else ''}")
    
    print("\nChecks:")
    print(f"  ✅ event: session present" if has_session_event else "  ❌ event: session missing")
    print(f"  ✅ data: chunks present ({data_chunk_count} chunks)" if has_data_chunks else "  ❌ data: chunks missing")
    print(f"  ✅ event: done present" if has_done_event else "  ❌ event: done missing")
    print(f"  ✅ Session ID returned: {session_id}" if session_id else "  ❌ Session ID missing")
    print(f"  ✅ Reply length > 30 chars ({len(full_reply)} chars)" if len(full_reply) > 30 else f"  ❌ Reply too short ({len(full_reply)} chars)")
    
    all_passed = (
        has_session_event and
        has_data_chunks and
        has_done_event and
        session_id and
        len(full_reply) > 30
    )
    
    if all_passed:
        print("\n✅ SSE format test PASSED")
    else:
        print("\n❌ SSE format test FAILED")
    
    return all_passed


async def main():
    result = await test_sse_format()
    exit(0 if result else 1)


if __name__ == "__main__":
    asyncio.run(main())
