"""CI Log Analysis System Ingestor Registry.

This module provides a decorator-based registry system for provider-specific
log ingestors with automatic discovery and instantiation capabilities.
"""
from typing import Dict, Type, Optional, Any, Callable, List
import inspect
import importlib
import pkgutil
from pathlib import Path

from ingestion.base import BaseLogIngestor  # Updated to absolute import
from utils.provider_detector import ProviderDetector  # Absolute import
from utils.buffered_stream_reader import BufferedStreamReader  # Absolute import

# Global registry to store ingestor classes by provider ID
INGESTOR_REGISTRY: Dict[str, Type[BaseLogIngestor]] = {}

def register_ingestor(provider_id: str, detection_patterns: Optional[dict] = None):
    """Decorator to register a class as an ingestor for a specific provider."""
    def decorator(cls: Type[BaseLogIngestor]) -> Type[BaseLogIngestor]:
        if not (inspect.isclass(cls) and issubclass(cls, BaseLogIngestor)):
            raise TypeError(f"Class {cls.__name__} must inherit from BaseLogIngestor")

        INGESTOR_REGISTRY[provider_id] = cls
        cls.provider_id = provider_id

        if detection_patterns:
            ProviderDetector.register_provider(
                provider_id,
                detection_patterns.get('strong_indicators', []),
                detection_patterns.get('weak_indicators', [])
            )

        return cls

    return decorator

def get_ingestor_class(provider_id: str) -> Type[BaseLogIngestor]:
    """Get the ingestor class for the specified provider."""
    try:
        return INGESTOR_REGISTRY[provider_id]
    except KeyError:
        raise KeyError(f"No ingestor registered for provider '{provider_id}'")

def get_registered_providers() -> List[str]:
    """Get a list of all registered provider IDs."""
    return list(INGESTOR_REGISTRY.keys())

def create_ingestor(file_path_or_handle, provider: Optional[str] = None, **config) -> BaseLogIngestor:
    """Factory function to create an appropriate ingestor instance."""
    file_handle = (
        file_path_or_handle if hasattr(file_path_or_handle, 'read')
        else BufferedStreamReader(file_path_or_handle)
    )

    if provider is None:
        pos = file_handle.tell() if hasattr(file_handle, 'tell') else None
        provider = ProviderDetector.detect_provider(file_handle)
        if pos is not None and hasattr(file_handle, 'seek'):
            file_handle.seek(pos)

    try:
        ingestor_class = get_ingestor_class(provider)
    except KeyError:
        from ingestion.generic import GenericLogIngestor  # Absolute import fallback
        ingestor_class = GenericLogIngestor

    return ingestor_class(file_handle, **config)

def discover_ingestors() -> None:
    """Automatically discover and import all ingestor modules in the ingestion package."""
    current_dir = Path(__file__).parent
    for (_, module_name, _) in pkgutil.iter_modules([str(current_dir)]):
        if module_name != "factory":
            importlib.import_module(f"ingestion.{module_name}")

# Trigger auto-discovery when module is imported
discover_ingestors()
