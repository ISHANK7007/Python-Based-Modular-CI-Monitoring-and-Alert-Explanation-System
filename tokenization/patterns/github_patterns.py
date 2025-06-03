import re

GITHUB_PATTERNS = [
    {
        "pattern": re.compile(r"FAIL:\s+.*", re.IGNORECASE),
        "type": "TEST_FAILURE"
    },
    {
        "pattern": re.compile(r"AssertionError:.*", re.IGNORECASE),
        "type": "ASSERTION_ERROR"
    },
    {
        "pattern": re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE),
        "type": "STACK_TRACE_START"
    },
    {
        "pattern": re.compile(r"ZeroDivisionError:.*", re.IGNORECASE),
        "type": "STACK_TRACE_LINE"
    },
    {
        "pattern": re.compile(r"Job failed.*", re.IGNORECASE),
        "type": "EXIT_CODE_NON_ZERO"
    },
    {
        "pattern": re.compile(r"Tests failed:.*", re.IGNORECASE),
        "type": "TEST_FAILURE"
    },
    {
        "pattern": re.compile(r"error.*", re.IGNORECASE),
        "type": "ERROR"
    },
    {
        "pattern": re.compile(r"warning.*", re.IGNORECASE),
        "type": "WARNING"
    },
]
