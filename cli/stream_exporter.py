import os
import markdown
from datetime import datetime

class StreamExporter:
    def __init__(self, export_dir="./ci-analysis-exports/"):
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)

    def export(self, segments, format="markdown", filename=None):
        if not segments:
            print("[Exporter] No segments to export.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = filename or f"export_{timestamp}.{self._ext(format)}"
        path = os.path.join(self.export_dir, filename)

        content = self._render(segments, format)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[Exporter] Exported {len(segments)} segments to {path}")

    def _render(self, segments, format):
        if format == "markdown":
            return self._render_markdown(segments)
        elif format == "html":
            md = self._render_markdown(segments)
            return markdown.markdown(md)
        else:
            return "\n".join(s.raw_text for s in segments)

    def _render_markdown(self, segments):
        lines = [f"# Exported CI Segment Report\n", f"Generated: {datetime.now()}\n"]
        for s in segments:
            lines.append(f"## Job ID: {getattr(s, 'job_id', 'N/A')}")
            lines.append(f"- **Segment ID**: {getattr(s, 'segment_id', 'N/A')}")
            lines.append(f"- **Label**: {getattr(s, 'segment_type', 'UNKNOWN')}")
            lines.append(f"- **Confidence**: {getattr(s, 'confidence', '--')}")
            lines.append(f"- **Text**: {getattr(s, 'raw_text', '').strip()}\n")
        return "\n".join(lines)

    def _ext(self, format):
        return "md" if format == "markdown" else "html" if format == "html" else "txt"
