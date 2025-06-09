def format_row(row):
    """
    Format a CI row for terminal output.
    Example fields: job_id, step, label, confidence, explanation_summary, status
    """
    return (
        f"{row.get('job_id', 'N/A')} | "
        f"{row.get('step', 'N/A')} | "
        f"{row.get('label', 'N/A')} | "
        f"[confidence: {row.get('confidence', 0.0):.2f}] | "
        f"{truncate(row.get('explanation_summary', ''), 80)} | "
        f"{render_status(row.get('status', 'INFO'))}"
    )

def truncate(text, max_length):
    return text if len(text) <= max_length else text[:max_length - 3] + "..."

def render_status(status):
    status = status.upper()
    if status == "FAIL":
        return "🔴 FAIL"
    elif status == "WARN":
        return "🟡 WARN"
    elif status == "PASS":
        return "🟢 PASS"
    else:
        return "ℹ️ INFO"
