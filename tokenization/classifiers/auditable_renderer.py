import os
import uuid
import time
import json
import hashlib
from datetime import datetime
from tokenization.classifiers.base_renderer import BaseRenderer
from tokenization.classifiers.verbosity_aware_renderer import VerbosityAwareRenderer

class AuditableRenderer(BaseRenderer, VerbosityAwareRenderer):
    """Renderer with comprehensive auditing and verbosity support"""

    format_name = "markdown"
    render_style = "auditable"
    VERSION = "1.0.0"

    def __init__(self, debug_level=0):
        super().__init__()
        self.debug_level = debug_level
        self.trace_data = {}
        self.trace_enabled = debug_level > 0
        self._start_time = None

    def render(self, template, data, job_context=None, verbosity=None):
        """Render with auditing and verbosity handling"""
        verbosity_level = verbosity if verbosity is not None else self.default_verbosity
        context = dict(data)
        context["verbosity"] = verbosity_level

        if self.trace_enabled:
            self._initialize_trace(template, data, job_context)
            self._start_time = time.time()

        try:
            result = super().render(template, context, job_context)

            if self.trace_enabled:
                self._finalize_trace(result)
                self._write_trace_file()

            return result

        except Exception as e:
            if self.trace_enabled:
                self._record_exception(e)
                self._write_trace_file()
            raise

    def _initialize_trace(self, template, data, job_context):
        """Set up the trace data structure"""
        self.trace_data = {
            "render_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "template_info": self._get_template_info(template),
            "input_data": self._sanitize_data(data),
            "job_context": self._sanitize_data(job_context) if job_context else None,
            "segment_processing": [],
            "template_variables": {},
            "placeholder_substitutions": [],
            "conditional_blocks": [],
            "performance_metrics": {},
            "cache_info": self._get_cache_info()
        }

    def _record_placeholder_substitution(self, placeholder, value, position, source):
        """Record a placeholder substitution"""
        if not self.trace_enabled:
            return
        self.trace_data["placeholder_substitutions"].append({
            "placeholder": placeholder,
            "value": str(value)[:100],
            "position": position,
            "source": source
        })

    def _record_segment_processing(self, segment, tokens, processing_time):
        """Record segment processing details"""
        if not self.trace_enabled or self.debug_level < 2:
            return
        self.trace_data["segment_processing"].append({
            "segment_id": segment.segment_id,
            "section": getattr(segment, "section", "unknown"),
            "processing_time_ms": int(processing_time * 1000),
            "token_matches": [
                {
                    "token": token.text[:50],
                    "confidence": token.confidence,
                    "position": [token.start, token.end]
                } for token in tokens[:10]
            ]
        })

    def _finalize_trace(self, result):
        """Finalize the trace with performance metrics"""
        end_time = time.time()
        total_time = end_time - self._start_time
        self.trace_data["performance_metrics"] = {
            "total_render_time_ms": int(total_time * 1000)
        }
        if self.debug_level >= 3:
            self.trace_data["result_hash"] = hashlib.sha256(result.encode("utf-8")).hexdigest()

    def _write_trace_file(self):
        """Write the trace to a file"""
        trace_dir = os.environ.get('RENDERER_TRACE_DIR', 'traces')
        os.makedirs(trace_dir, exist_ok=True)
        filename = os.path.join(trace_dir, f"render_trace_{self.trace_data['render_id']}.json")
        with open(filename, 'w') as f:
            json.dump(self.trace_data, f, indent=2, default=str)

    def _record_exception(self, exception):
        """Log an exception in the trace"""
        self.trace_data["exception"] = {
            "type": type(exception).__name__,
            "message": str(exception)
        }

    def _sanitize_data(self, data):
        """Sanitize data for safe JSON export"""
        try:
            return json.loads(json.dumps(data, default=str))
        except Exception:
            return str(data)

    def _get_template_info(self, template):
        """Extract template info"""
        return {
            "name": getattr(template, 'name', 'unknown'),
            "version": getattr(template, 'version', '1.0'),
            "source": getattr(template, 'source', '')
        }

    def _get_cache_info(self):
        """Stub for cache trace info"""
        return {
            "enabled": True,
            "hit_rate": "N/A"
        }
