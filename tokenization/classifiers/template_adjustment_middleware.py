class TemplateAdjustmentMiddleware:
    """Intercepts template rendering to apply feedback-based corrections."""
    
    def process_template(self, template, context, metadata):
        """Apply any relevant template corrections before final rendering."""
        # 1. Check for instance-specific patches
        instance_patches = self.feedback_store.find_instance_patches(
            job_id=metadata.job_id, 
            segment_id=metadata.segment_id
        )
        
        # 2. Apply label-specific patches
        label_patches = self.feedback_store.find_label_patches(
            label=context.label
        )
        
        # 3. Apply segment-type patches
        segment_patches = self.feedback_store.find_segment_patches(
            segment_type=metadata.segment_type
        )
        
        # 4. Apply global patches
        global_patches = self.feedback_store.find_global_patches()
        
        # Apply patches in order: instance → label → segment → global
        template = self._apply_patches(template, [
            *instance_patches, 
            *label_patches,
            *segment_patches,
            *global_patches
        ])
        
        return template