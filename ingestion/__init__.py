# ingestion/__init__.py

from .factory import create_ingestor
from .github_actions import GitHubActionsIngestor
from .gitlab import GitLabCIIngestor
from .generic import GenericLogIngestor


__all__ = ["create_ingestor", "GitHubActionsIngestor", "GitLabCIIngestor", "GenericIngestor"]
