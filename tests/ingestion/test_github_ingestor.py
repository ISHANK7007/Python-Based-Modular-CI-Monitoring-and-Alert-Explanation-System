ci_log_analysis/
├── cli/
│   ├── __init__.py
│   ├── main.py          # Contains main() function - primary entry point
│   ├── commands/        # Subcommand modules
│   │   ├── __init__.py
│   │   ├── analyze.py   # analyze command implementation
│   │   ├── export.py    # export command implementation
│   │   └── configure.py # configure command implementation 
│   └── utils/           # CLI-specific utilities
│       ├── __init__.py
│       ├── output.py    # Output formatting tools
│       └── config.py    # Config loading utilities