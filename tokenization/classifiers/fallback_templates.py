# Example fallback templates with placeholders
FALLBACK_TEMPLATES = {
    "environment": "The failure was likely due to {{context.environment_type}} environment instability. Consider retrying the build.",
    "timeout": "The job appears to have timed out. This could be due to resource constraints or long-running operations.",
    "dependency": "There may be an issue with external dependencies. Check for recent changes or service disruptions.",
    "generic": "The root cause could not be determined with confidence. Review the highlighted log sections for potential clues."
}