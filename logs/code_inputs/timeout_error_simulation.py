import time
import sys

def simulate_timeout_error():
    print("[INFO] Starting CI job step that will timeout...")
    try:
        # Simulate a long-running process
        time.sleep(15)  # Reduce this to 3–5 sec if testing manually
        print("[INFO] Job completed successfully (unexpected).")
    except KeyboardInterrupt:
        print("[ERROR] Job was manually interrupted.")
    finally:
        print("[ERROR] CI job timed out due to prolonged execution.")
        raise TimeoutError("Simulated timeout error: Job exceeded time limit.")

if __name__ == "__main__":
    simulate_timeout_error()
