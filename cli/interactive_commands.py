class InteractiveCommandHandler:
    """
    Maps keypresses to interactive CLI actions like feedback, expand, or cluster view.
    """

    def __init__(self):
        self.command_map = {
            "f": self.submit_feedback,
            "e": self.expand_explanation,
            "c": self.view_cluster_summary,
            "q": self.quit
        }

    def handle(self, key):
        action = self.command_map.get(key)
        if action:
            action()
        else:
            print(f"[Unknown Command] Key '{key}' is not bound to an action.")

    def submit_feedback(self):
        print("[Action] Submitting feedback... (stub)")

    def expand_explanation(self):
        print("[Action] Expanding explanation... (stub)")

    def view_cluster_summary(self):
        print("[Action] Displaying cluster summary... (stub)")

    def quit(self):
        print("[Action] Exiting interactive mode.")

# Example usage
if __name__ == "__main__":
    handler = InteractiveCommandHandler()
    for key in ["f", "e", "c", "x"]:
        handler.handle(key)
