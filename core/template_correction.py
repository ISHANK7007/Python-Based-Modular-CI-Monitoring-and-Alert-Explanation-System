# core/template_correction.py

from enum import Enum


class TemplateCorrection(Enum):
    """Defines types of feedback-driven corrections to be applied to templates."""
    
    FULL_REPLACEMENT = "full_replacement"            # Replace the entire template
    SECTION_OVERRIDE = "section_override"            # Override specific sections
    VARIABLE_PATCH = "variable_patch"                # Patch incorrect variable values
    EVIDENCE_REORDERING = "evidence_reordering"      # Reorder supporting evidence
    TERMINOLOGY_UPDATE = "terminology_update"        # Normalize inconsistent terminology
