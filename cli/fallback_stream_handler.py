class FallbackStreamHandler:
    """
    Displays placeholder rows for segments that are unclassified or pending explanation.
    """

    def render_pending_row(self, job_id, step="?", message="Pending explanation..."):
        return (
            f"{job_id} | {step} | ⚠️ UNCLASSIFIED | [confidence: --] | "
            f"{message} | ⚠️ PENDING"
        )

# Example usage (for testing):
if __name__ == "__main__":
    handler = FallbackStreamHandler()
    print(handler.render_pending_row("job_5678", "deploy"))
