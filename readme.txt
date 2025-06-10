# Python-Based Modular CI Monitoring and Alert Explanation System
## Project Objective
This project provides an intelligent, modular pipeline for analyzing Continuous Integration (CI) logs, automatically identifying root causes of failures, and offering human-readable explanations.
It supports GitHub Actions and GitLab CI, and includes:
- Real-time log ingestion and normalization
- Tokenization and segmentation of errors
- Root cause classification with confidence scoring
- Explanation rendering in Markdown/JSON
- Feedback-driven learning for classifier improvement
- Clustering of failure patterns
- Live CLI visualizations and YAML-based configuration
---
## Code Execution Screenshots
### Conversation 1: Execution Output
![Conversation 1 Execution](https://drive.google.com/file/d/1LZB6YIS19c3EY49fXRbD1t9L-8eMJwIP/view?usp=drive_link,https://drive.google.com/file/d/1eEfOxOnLVt4T0SqjU7Of5ivl1pbeG4lF/view?usp=drive_link)
### Conversation 2: Execution Output
![Conversation 2 Execution](https://drive.google.com/file/d/1UHvYkUI7Zjydkomt-XO7gUXLGOg02b8b/view?usp=drive_link, https://drive.google.com/file/d/15fsuZp_aUvjrFhUesmBhWaKzWsPCwfmd/view?usp=drive_link)
### Conversation 3: Execution Output
![Conversation 3 Execution](https://drive.google.com/file/d/18-hRo6d1CqGZ9dXiw08K76PnnhKpzPNJ/view?usp=drive_link)
### Conversation 4: Execution Output
![Conversation 4 Execution](https://drive.google.com/file/d/1LmOBDs3w7KCUcyewJxIG3BrzwJaSLG-q/view?usp=drive_link)
### Conversation 5: Execution Output
![Conversation 5 Execution](https://drive.google.com/file/d/1HPBnkcEoI74mF5Ud3lCwNzg2UfVrLoHf/view?usp=drive_link)
### Conversation 6: Execution Output
![Conversation 6 Execution](https://drive.google.com/file/d/1bxoH0zvGO0aOdwZ3sQLZ9idOlp4tay8k/view?usp=drive_link)
### Conversation 7: Execution Output
![Conversation 7 Execution](https://drive.google.com/file/d/1nVLdYC_CNqvSMGgKBBUoLlnaRkKBtwvN/view?usp=drive_link)
### Conversation 8: Execution Output
![Conversation 8 Execution](https://drive.google.com/file/d/1KbbzMPhAfyB67IBf1h5ji0tdeBNVlllh/view?usp=drive_link)
---
## Unit Test Outputs and Coverage
The following test cases validate critical components of the system across ingestion, tokenization, classification, feedback, clustering, and CLI modules.
### Conversation 2 Test Results
- **Test 1**: Basic tokenization with fallback matching
  ![Test 1](https://drive.google.com/file/d/1x2JS_1f8ku6xfbIP9nK3u5owAvC22CHm/view?usp=drive_link)
- **Test 2**: Error filtering with confidence scores
  ![Test 2](https://drive.google.com/file/d/1IRqy4UrUnEH2owIg4p1qUVfsdRl6429H/view?usp=drive_link)
- **Test 3**: Nested grouping validation
  ![Test 3](https://drive.google.com/file/d/1ONmW-FGNsix0c-zlWcIZy8jQ0uYWujFL/view?usp=drive_link)
### Conversation 3 Test Results
- **Test 4**: No-issue log ensures classifier skips clean logs
  ![Test 4](https://drive.google.com/file/d/1U2znr3UM5MRGxQKaU46at-XgTiphcQQz/view?usp=drive_link)
### Conversation 4 Test Results
- **Test 5**: Markdown rendering for fallback and valid explanations
  ![Test 5](https://drive.google.com/file/d/181FZ1GTe1UcWkuJlq8cwZ2Z5lWM3Ae1H/view?usp=drive_link)
### Conversation 5 Test Results
- **Test 6**: Feedback submission and confidence filtering
  ![Test 6](https://drive.google.com/file/d/1ledR3605r6abXtS7VTvwQ-8pVy1P3c8J/view?usp=drive_link)
### Conversation 6 Test Results
- **Test 7**: ClusterRanker selects correct cluster by similarity score
  ![Test 7](https://drive.google.com/file/d/1Gf5HfmORExcSH2wlcDl5vSxVg9AxpvC6/view?usp=drive_link)
### Conversation 7 Test Results
- **Test 8**: CLI interaction test simulating feedback keypress
  ![Test 8](https://drive.google.com/file/d/13AJJHv4Lldyg2edTFwFzXd2-Q-XxWZqC/view?usp=drive_link)
### Conversation 8 Test Results
- **Test 9**: End-to-end config test for segment injection and fallback
  ![Test 9](https://drive.google.com/file/d/1X94-QGyt8kCSGo3b7qErvo2TPDMGcGW7/view?usp=drive_link)
---
## Project Features Mapped to Conversations
- **Conversation 1**: Ingestor registry, log normalization, metadata tagging, GitHub/GitLab support
- **Conversation 2**: Tokenization pipeline, segment grouping, overlap resolution, and phrase filtering
- **Conversation 3**: Rule-based classification with confidence scoring and root cause prediction
- **Conversation 4**: Template renderer for Markdown/JSON output with traceability and evidence
- **Conversation 5**: Feedback ingestion, validation, and impact on classifiers and templates
- **Conversation 6**: Clustering jobs by failure type using token pattern and label similarity
- **Conversation 7**: Real-time CLI streaming, feedback interaction, stream filtering
- **Conversation 8**: Config loading, schema validation, integrated test corpus and CLI packaging

---
# CI Failure Simulation Inputs

## Directory: `logs/code_inputs/`
This directory contains Python scripts designed to simulate real CI job scenarios. These files can be executed directly or integrated into a GitHub Actions / GitLab CI pipeline to produce logs for testing the failure analysis system.

### Files Included:
- `syntax_error.py` → Contains a syntax error (missing colon)
- `oom_simulation.py` → Infinite loop with memory allocation to simulate OutOfMemory
- `failing_test.py` → Intentional assertion failure
- `clean_pass.py` → A valid script that runs without error
| `dependency_conflict_error.py` | This script simulates an environment where incompatible package versions are installed to trigger a dependency conflict.
- File: logs/code_inputs/dependency_conflict_error.py
- Scenario: Attempts to install `tensorflow==2.11.0` and `keras==2.8.0`, which are incompatible.
- Expected behavior: Installation fails and a `RuntimeError` is raised.
- Purpose: Used to generate realistic error logs in logs/generated/dependency_conflict.log for downstream testing and pipeline validation.| [`dependency_conflict.log`](logs/generated/dependency_conflict.log) |
| `timeout_error_simulation.py` | Simulates a CI job that stalls and exceeds its time quota. The script deliberately triggers a TimeoutError to mimic long-running or stuck processes that cause CI pipelines to abort due to timeout thresholds. Useful for validating timeout handling, alerting, and trace diagnostics. | [`timeout_error.log`](logs/generated/timeout_error.log) |

### Usage:
Run each script with Python and capture stderr to generate logs:
```bash
# Navigate to project root and run these:
python logs/code_inputs/syntax_error.py 2> output.log
python logs/code_inputs/oom_simulation.py 2> output.log
python logs/code_inputs/failing_test.py 2> output.log
python logs/code_inputs/clean_pass.py > output.log
python Output_code/logs/code_inputs/dependency_conflict_error.py 2> Output_code/logs/generated/dependency_conflict.log
python Output_code/logs/code_inputs/timeout_error_simulation.py 2> Output_code/logs/generated/timeout_error.log

```
### Input Code Execution Screenshots
- `syntax_error.py`
  ![syntax_error](https://drive.google.com/file/d/1-LEzd4X_QkNOdfL5G380ZnRm9vvViWMb/view?usp=drive_link)
- `oom_simulation.py`
  ![oom_simulation](https://drive.google.com/file/d/1cWfRS-rks47Z6MCex1lnEOWCMiqMtfZq/view?usp=drive_link)
- `failing_test.py`
  ![failing_test](https://drive.google.com/file/d/1yWccr1u5Y4Lylqga8Pxwk7Mh-UgpH2jY/view?usp=drive_link)
- `clean_pass.py`
  ![clean_pass](https://drive.google.com/file/d/1eVxvicWXvhXIkc3eadSn8TGNkRKN7ENA/view?usp=drive_link)
- `dependency_conflict_error.py`
  ![dependency_conflict_error](https://drive.google.com/file/d/1ze9Y8_-sQBb7YtboYg1kykkVNDTTAfTg/view?usp=drive_link)
- `timeout_error_simulation.py`
  ![timeout_error_simulation](https://drive.google.com/file/d/1jWZBtOalPJTVs9hfStct6I7iY9wKoU9s/view?usp=drive_linkd:\P16 data\Python-Based Modular)