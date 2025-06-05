from typing import Pattern, Callable, Optional

class ContextualRule:
    """
    A rule used for root cause classification with contextual awareness.
    """
    def __init__(self,
                 name: str,
                 pattern: Pattern,
                 classification: str,
                 context_fn: Optional[Callable] = None,
                 explanation: Optional[str] = None):
        self.name = name
        self.pattern = pattern
        self.classification = classification
        self.context_fn = context_fn
        self.explanation = explanation
