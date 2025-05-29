from typing import Dict, List, Optional, Tuple, Callable, Any
import re
from dataclasses import replace
import os

from core.models import LogLine

class MetadataRule:
    def __init__(self, name: str, pattern: str, fields: Dict[str, Any],
                 condition: Optional[Callable[[LogLine], bool]] = None,
                 priority: int = 100):
        self.name = name
        self.pattern = re.compile(pattern)
        self.fields = fields
        self.condition = condition or (lambda _: True)
        self.priority = priority

    def apply(self, log_line: LogLine) -> Tuple[bool, Dict[str, Any]]:
        if not self.condition(log_line):
            return False, {}
        match = self.pattern.search(log_line.raw_content)
        if not match:
            return False, {}

        fields_to_inject = {}
        for field_name, field_value in self.fields.items():
            if isinstance(field_value, str) and '\\' in field_value:
                try:
                    fields_to_inject[field_name] = match.expand(field_value)
                except (re.error, IndexError):
                    fields_to_inject[field_name] = field_value
            else:
                fields_to_inject[field_name] = field_value

        return True, fields_to_inject


class MetadataInjector:
    def __init__(self, rules: Optional[List[MetadataRule]] = None,
                 file_path: Optional[str] = None,
                 provider: Optional[str] = None):
        self.rules = rules or []
        self.file_path = file_path
        self.provider = provider
        self.context = {}
        self._setup_default_rules()

    def inject(self, log_line: LogLine) -> LogLine:
        fields_to_inject = self.context.copy()

        for rule in self.rules:
            matched, fields = rule.apply(log_line)
            if matched:
                fields_to_inject.update(fields)
                for field_name in ['provider', 'step_name', 'section', 'job_id']:
                    if field_name in fields and fields[field_name]:
                        self.context[field_name] = fields[field_name]

        if 'tags' in fields_to_inject and hasattr(log_line, 'tags') and log_line.tags:
            existing_tags = log_line.tags if isinstance(log_line.tags, list) else [log_line.tags]
            new_tags = fields_to_inject['tags'] if isinstance(fields_to_inject['tags'], list) else [fields_to_inject['tags']]
            fields_to_inject['tags'] = list(set(existing_tags + new_tags))

        return replace(log_line, **fields_to_inject)

    def add_rule(self, rule: MetadataRule):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.priority)

    def _setup_default_rules(self):
        if self.provider:
            self.add_rule(MetadataRule(
                name="explicit_provider",
                pattern=r".*",
                fields={"provider": self.provider},
                priority=1000
            ))

        if self.file_path:
            self._add_file_path_rules()
        self._add_common_rules()
        self._add_github_rules()
        self._add_gitlab_rules()
        self._add_jenkins_rules()
        self._add_azure_rules()

    def _add_file_path_rules(self):
        filename = os.path.basename(self.file_path).lower()
        if 'github' in filename or 'actions' in filename:
            self.add_rule(MetadataRule("github_file_hint", r".*", {"provider": "github"}, priority=900))
        if 'gitlab' in filename or 'gitlab-ci' in filename:
            self.add_rule(MetadataRule("gitlab_file_hint", r".*", {"provider": "gitlab"}, priority=900))
        if 'jenkins' in filename or 'console.log' in filename:
            self.add_rule(MetadataRule("jenkins_file_hint", r".*", {"provider": "jenkins"}, priority=900))

    def _add_common_rules(self):
        self.add_rule(MetadataRule("error_detection", r"(?i)(error|exception|fail|traceback)\b", {"level": "ERROR", "tags": ["error"]}, priority=500))
        self.add_rule(MetadataRule("warning_detection", r"(?i)(warning|warn|caution|attention)\b", {"level": "WARNING", "tags": ["warning"]}, priority=500))
        self.add_rule(MetadataRule("common_timestamp", r"(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[-+]\d{2}:\d{2})?)", {"raw_timestamp": "\\1"}, priority=600))
        self.add_rule(MetadataRule("common_log_level", r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL|FATAL)\b", {"raw_level": "\\1"}, priority=600))

    def _add_github_rules(self):
        self.add_rule(MetadataRule("github_detection", r"##\[(group|endgroup|section|command|step)\]", {"provider": "github"}, priority=800))
        self.add_rule(MetadataRule("github_step", r"##\[step\](.*)", {"step_name": "\\1", "section": "\\1"}, priority=700))
        self.add_rule(MetadataRule("github_group", r"##\[group\](.*)", {"section": "\\1"}, priority=700))
        self.add_rule(MetadataRule("github_command", r"##\[command\](.*)", {"stream_type": "command", "tags": ["command"]}, priority=700))
        self.add_rule(MetadataRule("github_stdout", r"^\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s", {"stream_type": "stdout"}, condition=lambda l: not l.stream_type, priority=600))

    def _add_gitlab_rules(self):
        self.add_rule(MetadataRule("gitlab_detection", r"section_(start|end):\d+:", {"provider": "gitlab"}, priority=800))
        self.add_rule(MetadataRule("gitlab_section", r"section_start:\d+:([^\s]+)", {"section": "\\1"}, priority=700))
        self.add_rule(MetadataRule("gitlab_runner", r"Running with gitlab-runner", {"stream_type": "system", "tags": ["runner"]}, priority=700))
        self.add_rule(MetadataRule("gitlab_job", r"Running on runner-[^\s]+ via ([^\s]+)", {"job_id": "\\1"}, priority=700))

    def _add_jenkins_rules(self):
        pass  # You can implement Jenkins-specific rules here

    def _add_azure_rules(self):
        pass  # You can implement Azure-specific rules here
