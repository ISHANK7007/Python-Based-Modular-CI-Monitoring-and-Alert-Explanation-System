import sys
import os
import unittest

# Ensure the parent directory (project root) is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.cluster_ranker import ClusterRanker
from core.models import ClusterCandidate, JobRecord


class TestClusterRanker(unittest.TestCase):
    
    def test_single_cluster_assignment_TC1(self):
        # TC1: Input: 5 jobs with label=TEST_FAILURE, all sharing same token pattern.
        cluster_id = "cluster-001"
        label = "TEST_FAILURE"
        token_pattern = {"tokens": ["assert", "failed"], "weight": 0.9}

        cluster = ClusterCandidate(
            cluster_id=cluster_id,
            canonical_label=label,
            token_pattern=token_pattern,
            jobs=[
                JobRecord(job_id=f"job-{i}", confidence=0.9, membership_score=0.95)
                for i in range(1, 6)
            ]
        )

        ranker = ClusterRanker()
        selected = ranker.select_best_cluster("job-6", [cluster])

        self.assertEqual(selected.cluster_id, cluster_id)
        print(f"\n✅ TC1 Output: Selected cluster ID: {selected.cluster_id}, Members: {len(cluster.jobs)}")

    def test_equal_score_conflict_TC2(self):
        # TC2: One job matches two clusters with equal score.
        job_id = "job-9"

        cluster1 = ClusterCandidate(
            cluster_id="cluster-101",
            canonical_label="FLAKY_TEST",
            token_pattern={"tokens": ["flaky", "retry"], "weight": 0.75},
            jobs=[
                JobRecord(job_id="j1", confidence=0.85, membership_score=0.9),
                JobRecord(job_id="j2", confidence=0.82, membership_score=0.9),
            ]
        )

        cluster2 = ClusterCandidate(
            cluster_id="cluster-102",
            canonical_label="FLAKY_TEST",
            token_pattern={"tokens": ["flaky", "retry"], "weight": 0.75},
            jobs=[
                JobRecord(job_id="j3", confidence=0.88, membership_score=0.9),
                JobRecord(job_id="j4", confidence=0.76, membership_score=0.9),
            ]
        )

        ranker = ClusterRanker()
        best_cluster = ranker.select_best_cluster(job_id, [cluster1, cluster2])

        self.assertIn(best_cluster.cluster_id, ["cluster-101", "cluster-102"])
        print(f"\n✅ TC2 Output: Selected cluster ID: {best_cluster.cluster_id}, Label: {best_cluster.canonical_label}")


if __name__ == '__main__':
    unittest.main()
