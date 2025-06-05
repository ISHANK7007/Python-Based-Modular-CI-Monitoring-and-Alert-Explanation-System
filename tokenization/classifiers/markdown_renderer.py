from abc import ABC, abstractmethod
from typing import List
from core.root_cause_prediction import RootCausePrediction

class BaseRenderer(ABC):
    """Abstract base class for explanation renderers."""

    @abstractmethod
    def render(self, predictions: List[RootCausePrediction]) -> str:
        pass


class GitHubMarkdownRenderer(BaseRenderer):
    """Renders root cause explanations in GitHub-flavored markdown."""

    def render(self, predictions: List[RootCausePrediction]) -> str:
        if not predictions:
            return "### ❗ No root cause predictions found."

        output_lines = ["### 🔍 Root Cause Analysis Report", ""]
        for pred in predictions:
            output_lines.append(f"#### 🔹 {pred.label} (Confidence: {pred.confidence:.2f})")
            if pred.supporting_tokens:
                output_lines.append("**Evidence Tokens:**")
                output_lines.append(", ".join(pred.supporting_tokens))
            if hasattr(pred, "segment_ids"):
                output_lines.append(f"**Affected Segment(s):** {', '.join(pred.segment_ids)}")
            if pred.metadata:
                output_lines.append("**Metadata:**")
                for key, value in pred.metadata.items():
                    output_lines.append(f"- {key}: {value}")
            output_lines.append("")  # Spacing between blocks
        return "\n".join(output_lines)


class VerbosityAwareRenderer(GitHubMarkdownRenderer):
    """Extends GitHubMarkdownRenderer with verbosity-aware rendering."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose

    def render(self, predictions: List[RootCausePrediction]) -> str:
        if not predictions:
            return (
                "### ⚠️ No root cause explanations were confidently detected.\n"
                "> Try reviewing build logs manually or increasing classifier sensitivity."
            )

        output_lines = ["### 🧠 CI Log Root Cause Summary", ""]
        for pred in predictions:
            output_lines.append(f"#### 🪵 {pred.label} ({pred.confidence:.2f})")

            if self.verbose and pred.supporting_tokens:
                output_lines.append("```log")
                output_lines.extend(pred.supporting_tokens)
                output_lines.append("```")

            if pred.metadata and self.verbose:
                output_lines.append("**Metadata:**")
                for key, value in pred.metadata.items():
                    output_lines.append(f"- {key}: {value}")

            output_lines.append("")  # gap
        return "\n".join(output_lines)
