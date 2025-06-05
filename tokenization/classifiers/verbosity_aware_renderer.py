from typing import Optional
from tokenization.classifiers.context_segment_renderer import MarkdownRenderer

# Assume MarkdownRenderer already inherits from ITemplateRenderer and sets self.default_verbosity
class VerbosityAwareRenderer(MarkdownRenderer):
    """Renderer that adapts content based on verbosity level"""

    def render(self, template, data, job_context=None, verbosity: Optional[int] = None):
        """Render with verbosity control"""
        # Determine effective verbosity
        effective_verbosity = verbosity if verbosity is not None else self.default_verbosity

        # Add verbosity and symbolic constants to the rendering context
        context = dict(data)
        context['verbosity'] = effective_verbosity
        context['MINIMAL'] = self.MINIMAL
        context['STANDARD'] = self.STANDARD
        context['VERBOSE'] = self.VERBOSE
        context['DIAGNOSTIC'] = self.DIAGNOSTIC

        # Filter segments based on verbosity
        self._configure_segments_for_verbosity(effective_verbosity)

        # Perform rendering
        return super().render(template, context, job_context)

    def _configure_segments_for_verbosity(self, verbosity: int):
        """Filter and prioritize segments based on verbosity level"""
        if not hasattr(self, 'segments') or not self.segments:
            self.active_segments = []
            return

        if verbosity == self.MINIMAL:
            threshold = 0.8
            max_segments = 1
        elif verbosity == self.STANDARD:
            threshold = 0.5
            max_segments = 3
        elif verbosity == self.VERBOSE:
            threshold = 0.2
            max_segments = 8
        else:  # DIAGNOSTIC
            threshold = 0.0
            max_segments = float('inf')

        # Filter and sort by relevance
        filtered = [s for s in self.segments if s.relevance >= threshold]
        filtered.sort(key=lambda s: s.relevance, reverse=True)
        self.active_segments = filtered[:int(max_segments)]

        # Trace verbosity filtering if auditing is enabled
        if hasattr(self, 'trace_data'):
            self.trace_data['verbosity'] = {
                'level': verbosity,
                'threshold': threshold,
                'max_segments': max_segments,
                'included_segments': len(self.active_segments),
                'total_segments': len(self.segments)
            }
