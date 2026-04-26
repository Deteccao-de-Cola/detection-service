import random
import numpy as np


class KMeansLevenshteinService:

    @staticmethod
    def hamming_distance(a, b):
        if len(a) != len(b):
            raise ValueError("Sequences must be of equal length")
        distance = 0
        for i in range(len(a)):
            if a[i] != b[i]:
                distance += 1
        return distance

    @staticmethod
    def hamming_similarity(seq1, seq2):
        """
        Pairwise similarity compatible with ComparisonService.compare.
        seq1, seq2 are sets or lists of (itemId, respostaUsuario) tuples.
        Sorts by itemId to ensure consistent ordering before comparison.
        Returns float 0.0-1.0.
        """
        s1 = [r for _, r in sorted(seq1, key=lambda x: x[0])]
        s2 = [r for _, r in sorted(seq2, key=lambda x: x[0])]

        n = max(len(s1), len(s2))
        if n == 0:
            return 1.0

        dist = KMeansLevenshteinService.hamming_distance(s1, s2)
        return (n - dist) / n

    @staticmethod
    def kmeans_hamming(responses_cache, k=2, max_iter=10):
        """
        K-means clustering using Hamming distance.
        responses_cache: dict {user_id: [{'itemId': ..., 'respostaUsuario': ...}, ...]}
        Returns: dict {user_id: cluster_id}
        """
        user_ids = list(responses_cache.keys())
        sequences = [
            [item['respostaUsuario'] for item in sorted(responses_cache[uid], key=lambda x: x['itemId'])]
            for uid in user_ids
        ]

        if len(sequences) < k:
            return {uid: 0 for uid in user_ids}

        centers = random.sample(sequences, k)

        for _ in range(max_iter):
            clusters = {i: [] for i in range(k)}

            for seq in sequences:
                distances = [KMeansLevenshteinService.hamming_distance(seq, c) for c in centers]
                cluster_id = int(np.argmin(distances))
                clusters[cluster_id].append(seq)

            new_centers = []
            for cluster in clusters.values():
                if not cluster:
                    new_centers.append(random.choice(sequences))
                    continue
                center = []
                for i in range(len(cluster[0])):
                    values = [seq[i] for seq in cluster if i < len(seq)]
                    center.append(max(set(values), key=values.count))
                new_centers.append(center)

            centers = new_centers

        student_clusters = {}
        for uid, seq in zip(user_ids, sequences):
            distances = [KMeansLevenshteinService.hamming_distance(seq, c) for c in centers]
            student_clusters[uid] = int(np.argmin(distances))

        return student_clusters
