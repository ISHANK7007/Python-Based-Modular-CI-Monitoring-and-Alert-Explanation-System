from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class JobContext:
    """Context data for a CI job"""
    job_id: str
    provider: str
    workflow_name: Optional[str] = None
    step_name: Optional[str] = None
    branch: Optional[str] = None
    commit_sha: Optional[str] = None
    timestamp: Optional[str] = None
    repository: Optional[str] = None
    actor: Optional[str] = None
    url_template: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering"""
        return asdict(self)
