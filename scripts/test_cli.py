import asyncio
import json
import sys
import logging

from aerocaliper import AeroCaliperAgent, logger

# Disable CloudLoggingHandler locally to avoid background thread quota errors
logger.handlers.clear()
logger.addHandler(logging.StreamHandler(sys.stdout))

async def run_cli_test(policy="finops"):
    queue = asyncio.Queue()
    approval_event = asyncio.Event()
    agent = AeroCaliperAgent(event_queue=queue, approval_event=approval_event, target_use_case=policy)

    async def print_events():
        while True:
            msg = await queue.get()
            if msg == "__DONE__":
                break
            
            try:
                event = json.loads(msg)
                event_type = event.get("type")
                if event_type == "log":
                    print(f"[{event.get('level', 'INFO').upper()}] {event.get('msg')}")
                elif event_type == "candidate_prompt":
                    print(f"\n--- [A2UI APPROVAL] Generated Candidate Prompt ---\n{event.get('prompt')}\n-------------------------------------------------")
                    print("\n[CLI] Automatically approving the prompt to continue the pipeline...\n")
                    # Automatically approve to continue the pipeline in CLI
                    agent.approval_granted = True
                    approval_event.set()
                elif event_type == "patch_deployed":
                    print(f"[SUCCESS] Patch successfully deployed!\n{event.get('patched_prompt')}")
                elif event_type == "backtest_metrics":
                    print(f"[METRICS] Backtest Results: {event.get('pass_rate')}% ({event.get('passed_cases')}/{event.get('total_cases')})")
                else:
                    print(f"[EVENT] {event_type}: {event}")
            except Exception as e:
                print(f"[RAW OUTPUT] {msg}")

    print(f"\nStarting CLI Test for policy: {policy.upper()}")
    print("="*50)
    
    # Start the event printer
    printer_task = asyncio.create_task(print_events())
    
    try:
        result = await agent.execute_remediation()
        print("\n[DONE] Pipeline execution completed successfully!")
        print("Final Result:", result.get("patched_prompt")[:100], "...")
    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
    finally:
        await queue.put("__DONE__")
        await printer_task

if __name__ == "__main__":
    policy = sys.argv[1] if len(sys.argv) > 1 else "finops"
    asyncio.run(run_cli_test(policy))
