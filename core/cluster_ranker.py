# core/cluster_ranker.py

from typing import List, Optional
from core.models import ClusterCandidate, JobRecord

class ClusterRanker:
    def select_best_cluster(self, job_id: str, clusters: List[ClusterCandidate]) -> Optional[ClusterCandidate]:
        if not clusters:
            return None

        # Compute median confidence for each cluster
        def median_confidence(cluster: ClusterCandidate) -> float:
            confidences = [job.confidence for job in cluster.jobs if job.job_id == job_id or job.label]
            if not confidences:
                return 0.0
            sorted_vals = sorted(confidences)
            n = len(sorted_vals)
            mid = n // 2
            return (sorted_vals[mid] if n % 2 == 1 else (sorted_vals[mid - 1] + sorted_vals[mid]) / 2)

        ranked = sorted(
            clusters,
            key=lambda c: (median_confidence(c), len(c.jobs)),
            reverse=True
        )

        return ranked[0]
