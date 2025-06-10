from subprocess import run, PIPE

def simulate_dependency_conflict():
    print("[INFO] Installing conflicting dependencies...")
    result = run(
        ["pip", "install", "tensorflow==2.11.0", "keras==2.8.0"],
        stdout=PIPE,
        stderr=PIPE,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print("[ERROR] Dependency installation failed:")
        print(result.stderr)
        raise RuntimeError("Dependency conflict detected")

if __name__ == "__main__":
    simulate_dependency_conflict()
