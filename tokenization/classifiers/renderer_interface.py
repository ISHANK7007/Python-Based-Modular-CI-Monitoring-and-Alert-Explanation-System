from abc import ABC, abstractmethod


class ITemplateRenderer(ABC):
    """Interface for explanation renderers with verbosity control"""

    # Verbosity level constants
    MINIMAL = 0
    STANDARD = 1
    VERBOSE = 2
    DIAGNOSTIC = 3

    def __init__(self, default_verbosity=STANDARD):
        self.default_verbosity = default_verbosity

    @abstractmethod
    def render(self, template, data, job_context=None, verbosity=None):
        """
        Render the template with the specified verbosity level.

        Args:
            template: The template object to render
            data: Dictionary or object containing render variables
            job_context: Optional job metadata context (e.g., job_id, section)
            verbosity: Verbosity level (MINIMAL, STANDARD, VERBOSE, DIAGNOSTIC)
                       If None, uses self.default_verbosity

        Returns:
            str: The rendered explanation output
        """
        pass
