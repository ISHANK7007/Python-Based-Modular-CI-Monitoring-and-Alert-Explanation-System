# tokenization/context_rules.py

# Define a list of context rules (can be regex patterns or callable rules)
default_context_rules = [
    {
        "pattern": r"Traceback \(most recent call last\):",
        "context": "stack_trace",
        "scope_cues": ["exception", "traceback"]
    },
    {
        "pattern": r"Job failed",
        "context": "job_failure",
        "scope_cues": ["exit_code", "summary"]
    },
    {
        "pattern": r"Tests failed",
        "context": "test_summary",
        "scope_cues": ["test_result"]
    }
]
