from collections import defaultdict, Counter
from typing import List, Dict


class BatchOptimizedExplanationEngine:
    def __init__(self, template_engine, segment_processor, cache_manager):
        self.template_engine = template_engine
        self.segment_processor = segment_processor
        self.cache_manager = cache_manager
        self.render_statistics = defaultdict(Counter)

    def batch_generate(self, predictions_batch: List, format_type: str = "markdown") -> List[str]:
        """Generate explanations for a batch of predictions with optimizations"""
        results = []
        cache_hits = 0

        # Group similar predictions to optimize rendering
        prediction_groups = self._group_by_similarity(predictions_batch)

        for group in prediction_groups:
            template_key = self._get_template_cache_key(group[0], format_type)
            template_rendered = self.cache_manager.get(template_key)

            if not template_rendered:
                template = self._select_template(group[0])
                renderer = self._get_renderer(format_type)
                template_rendered = renderer.render_template_skeleton(template)
                self.cache_manager.set(template_key, template_rendered)
            else:
                cache_hits += 1

            for prediction in group:
                segments = self._get_segments(prediction)
                processed_segments = self._process_segments(segments)
                explanation = self._fill_template(template_rendered, prediction, processed_segments)
                results.append(explanation)

        self.render_statistics[format_type]['cache_hits'] = cache_hits
        self.render_statistics[format_type]['total'] = len(predictions_batch)

        return results

    def _get_segments(self, prediction) -> List:
        """Get segments with caching optimization"""
        segments = []
        for segment_id in prediction.segment_ids:
            cache_key = f"segment:{segment_id}"
            cached = self.cache_manager.get(cache_key)
            if cached:
                segments.append(cached)
            else:
                segment = self.segment_processor.get_segment(segment_id)
                self.cache_manager.set(cache_key, segment)
                segments.append(segment)
        return segments

    def _group_by_similarity(self, predictions_batch: List) -> List[List]:
        """Group predictions by label or metadata to allow template reuse"""
        groups = defaultdict(list)
        for pred in predictions_batch:
            key = (pred.label, pred.metadata.get("provider", "generic"))
            groups[key].append(pred)
        return list(groups.values())

    def _get_template_cache_key(self, prediction, format_type: str) -> str:
        """Generate a cache key based on label, provider, and format"""
        label = prediction.label
        provider = prediction.metadata.get("provider", "generic")
        confidence = prediction.confidence
        return f"tpl:{label}|provider:{provider}|format:{format_type}|conf:{int(confidence * 10)}"

    def _select_template(self, prediction):
        """Stub for selecting a template from engine"""
        return self.template_engine.get_template(prediction.label)

    def _get_renderer(self, format_type: str):
        """Stub for fetching renderer based on format"""
        return self.template_engine.get_renderer(format_type)

    def _process_segments(self, segments: List) -> List:
        """Stub for processing segment list"""
        return [self.segment_processor.process(segment) for segment in segments]

    def _fill_template(self, template_rendered: str, prediction, segments: List) -> str:
        """Stub for injecting data into a rendered template skeleton"""
        return template_rendered.format(
            label=prediction.label,
            segments="\n".join(s.content for s in segments),
            confidence=f"{prediction.confidence:.2f}"
        )
