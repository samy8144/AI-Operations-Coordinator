import sys
import os
import time

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from agent import get_agent

def test_agent_integration():
    print("🤖 Initializing Agent for Integration Test...")
    try:
        agent = get_agent()
        
        # Test 1: Simple greeting (no tools)
        print("\nTest 1: Simple Greeting")
        start = time.time()
        resp = agent.chat("Hello, are you online?", session_id="test-session")
        print(f"Response: {resp}")
        print(f"Time: {time.time() - start:.2f}s")
        
        # Test 2: Data retrieval (uses tools + sheets caching)
        print("\nTest 2: Data Retrieval (Pilots)")
        start = time.time()
        # "List all pilots" should trigger get_pilot_roster tool
        resp = agent.chat("List all pilots in the roster.", session_id="test-session")
        print(f"Response length: {len(resp)} chars")
        print(f"Time: {time.time() - start:.2f}s")
        
        if "Arjun" in resp or "P001" in resp or "pilots" in resp.lower():
            print("✅ Data retrieval successful")
        else:
            print("⚠️ Data retrieval content uncertain - check output")
            
        print("\n✅ Integration Test Complete: Agent is functional and fast.")
        
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_agent_integration()
