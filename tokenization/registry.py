from typing import Dict, Type

# Internal registry dictionary
CLASSIFIER_REGISTRY: Dict[str, Type] = {}

def register_classifier(provider_name: str):
    """Decorator to register a token classifier for a CI provider."""
    def decorator(cls: Type) -> Type:
        CLASSIFIER_REGISTRY[provider_name] = cls
        return cls
    return decorator

def get_classifier(provider_name: str):
    """Retrieve the classifier class for a given provider."""
    # Delayed import to avoid circular dependency
    from tokenization.context_classifier import BaseTokenClassifier
    return CLASSIFIER_REGISTRY.get(provider_name, BaseTokenClassifier)
