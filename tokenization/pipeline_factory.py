from typing import Dict, Any, List
from tokenization.pipeline import TokenizationPipeline
from tokenization.segment_classifier import SegmentClassifier, ClassificationRule
from tokenization.context_analyzer import ContextAnalyzer
from tokenization.grouping import CommandOutputGrouping, SectionBasedGrouping
from tokenization.token_types import TokenType
from tokenization.tokenization_cache import TokenizationCache
from tokenization.context_classifier import ContextAwareClassifier
from tokenization.grouped_segment import GroupedSegment
from tokenization.pattern_tokenizer import PatternBasedTokenizer
from tokenization.provider_aware_tokenizer import ProviderAwareTokenizer


class TokenizationPipelineFactory:
    """Factory for creating tokenization pipelines optimized for different use cases."""

    @classmethod
    def create_default_pipeline(cls, config: Dict[str, Any] = None) -> TokenizationPipeline:
        """Create a default tokenization pipeline with standard components."""
        config = config or {}

        # Initialize tokenizer (provider-aware)
        tokenizer = cls._create_provider_aware_tokenizer(config)

        # Initialize segment classifier with standard rules
        segment_classifier = cls._create_standard_classifier(config)

        # Initialize context analyzer
        context_analyzer = ContextAnalyzer(
            window_size=config.get('context_window_size', 5),
            providers_config=config.get('providers_config', {})
        )

        # Initialize grouping strategy - default to command output grouping
        grouping_strategy = CommandOutputGrouping()

        return TokenizationPipeline(
            tokenizer=tokenizer,
            segment_classifier=segment_classifier,
            context_analyzer=context_analyzer,
            grouping_strategy=grouping_strategy,
            config=config
        )

    @classmethod
    def create_section_aware_pipeline(cls, config: Dict[str, Any] = None) -> TokenizationPipeline:
        """Create a pipeline optimized for section-based analysis."""
        pipeline = cls.create_default_pipeline(config)
        pipeline.grouping_strategy = SectionBasedGrouping()
        return pipeline

    @classmethod
    def _create_provider_aware_tokenizer(cls, config: Dict[str, Any]) -> ProviderAwareTokenizer:
        """Create a provider-aware tokenizer with specialized tokenizers for each provider."""
        tokenizers = {}

        # GitHub Actions Tokenizer
        if 'github' not in config.get('disabled_providers', []):
            tokenizers['github'] = PatternBasedTokenizer(
                patterns=cls._get_github_patterns(),
                config=config.get('github_tokenizer_config', {})
            )

        # GitLab CI Tokenizer
        if 'gitlab' not in config.get('disabled_providers', []):
            tokenizers['gitlab'] = PatternBasedTokenizer(
                patterns=cls._get_gitlab_patterns(),
                config=config.get('gitlab_tokenizer_config', {})
            )

        # Default tokenizer for unknown providers
        default_tokenizer = PatternBasedTokenizer(
            patterns=cls._get_generic_patterns(),
            config=config.get('default_tokenizer_config', {})
        )

        return ProviderAwareTokenizer(
            tokenizers=tokenizers,
            default_tokenizer=default_tokenizer,
            config=config.get('provider_aware_tokenizer_config', {})
        )

    @classmethod
    def _get_github_patterns(cls) -> Dict[TokenType, List[str]]:
        """Get GitHub-specific tokenization patterns."""
        return {
            TokenType.SECTION_START: [r'^##\[group\]'],
            TokenType.SECTION_END: [r'^##\[endgroup\]'],
            TokenType.ERROR: [r'error:.*'],
            TokenType.WARNING: [r'warning:.*'],
            TokenType.INFO: [r'info:.*'],
        }

    @classmethod
    def _get_gitlab_patterns(cls) -> Dict[TokenType, List[str]]:
        """Get GitLab-specific tokenization patterns."""
        return {
            TokenType.SECTION_START: [r'^section_start:.*'],
            TokenType.SECTION_END: [r'^section_end:.*'],
            TokenType.ERROR: [r'\[ERROR\] .*'],
            TokenType.WARNING: [r'\[WARNING\] .*'],
            TokenType.INFO: [r'\[INFO\] .*'],
        }

    @classmethod
    def _get_generic_patterns(cls) -> Dict[TokenType, List[str]]:
        """Get generic tokenization patterns."""
        return {
            TokenType.ERROR: [r'(?i)error.*'],
            TokenType.WARNING: [r'(?i)warn.*'],
            TokenType.INFO: [r'(?i)info.*'],
            TokenType.DEBUG: [r'(?i)debug.*'],
            TokenType.COMMAND: [r'^\$ .*'],
        }

    @classmethod
    def _create_standard_classifier(cls, config: Dict[str, Any]) -> SegmentClassifier:
        """Create a standard segment classifier with common classification rules."""
        # Placeholder for a list of rules. Should be replaced with actual rule implementations.
        rules: List[ClassificationRule] = []
        return SegmentClassifier(classification_rules=rules, config=config)
