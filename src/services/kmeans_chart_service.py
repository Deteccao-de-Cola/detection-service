import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PUBLIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'public')


class KmeansChartService:

    @staticmethod
    def _avg_intra_cluster_distance(sequences):
        n = len(sequences)
        if n < 2:
            return 0.0

        total = 0
        pairs = 0
        for i in range(n):
            for j in range(i + 1, n):
                total += sum(a != b for a, b in zip(sequences[i], sequences[j]))
                pairs += 1

        return total / pairs

    @staticmethod
    def compute_cluster_stats(student_clusters, sequences_by_user):
        grouped = {}
        for uid, cluster_id in student_clusters.items():
            grouped.setdefault(cluster_id, []).append(sequences_by_user[uid])

        return {
            cluster_id: {
                'size': len(sequences),
                'avg_intra_distance': KmeansChartService._avg_intra_cluster_distance(sequences),
            }
            for cluster_id, sequences in grouped.items()
        }

    @staticmethod
    def generate_cluster_distribution_chart(cluster_stats, exam_id):
        cluster_ids = sorted(cluster_stats.keys())
        labels = [f'Cluster {c}' for c in cluster_ids]
        sizes = [cluster_stats[c]['size'] for c in cluster_ids]
        avg_distances = [cluster_stats[c]['avg_intra_distance'] for c in cluster_ids]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

        ax1.bar(labels, sizes, color='#4C72B0')
        ax1.set_title('Alunos por cluster')
        ax1.set_ylabel('Quantidade de alunos')
        for i, v in enumerate(sizes):
            ax1.text(i, v, str(v), ha='center', va='bottom')

        ax2.bar(labels, avg_distances, color='#C44E52')
        ax2.set_title('Distância média intra-cluster (Hamming)')
        ax2.set_ylabel('Distância média')
        for i, v in enumerate(avg_distances):
            ax2.text(i, v, f'{v:.2f}', ha='center', va='bottom')

        fig.suptitle(f'K-means (Hamming) — Prova {exam_id}', fontweight='bold')
        plt.tight_layout()

        filename = f'kmeans_clusters_{exam_id}.png'
        filepath = os.path.join(PUBLIC_DIR, filename)
        plt.savefig(filepath, dpi=120)
        plt.close(fig)

        return filename
