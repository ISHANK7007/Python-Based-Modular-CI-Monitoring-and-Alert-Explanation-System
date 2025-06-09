# tokenization/classifiers/template_adjustment_middleware.py

class DummyFeedbackStore:
    def find_instance_patches(self, job_id, segment_id, segment):
        # Return dummy patches for testing
        return [{"search": "{{segment.summary}}", "replace": "Build failed due to missing symbol"}]

    def find_label_patches(self, label):
        return []

    def find_segment_patches(self, segment_type):
        return []

    def find_global_patches(self):
        return []


class TemplateAdjustmentMiddleware:
    def __init__(self, feedback_store=None):
        self.feedback_store = feedback_store or DummyFeedbackStore()

    def process_template(self, template, context, metadata):
        segment = context["segment"]

        instance_patches = self.feedback_store.find_instance_patches(
            job_id=metadata.job_id,
            segment_id=metadata.segment_id,
            segment=segment
        )

        label_patches = self.feedback_store.find_label_patches(
            label=segment.label
        )

        segment_patches = self.feedback_store.find_segment_patches(
            segment_type=metadata.segment_type
        )

        global_patches = self.feedback_store.find_global_patches()

        return self._apply_patches(template, [
            *instance_patches,
            *label_patches,
            *segment_patches,
            *global_patches
        ])

    def _apply_patches(self, template, patches):
        for patch in patches:
            if patch.get("search") in template:
                template = template.replace(patch["search"], patch["replace"])
        return template
