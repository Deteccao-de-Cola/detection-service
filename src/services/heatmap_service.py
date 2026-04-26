import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PUBLIC_DIR = os.path.join(os.path.dirname(__file__), '..', 'public')


class HeatmapService:

    @staticmethod
    def generate_jaccard_heatmap(comparison_matrix: list, exam_id: int, top_n: int = 50) -> str:
        # top N users by max jaccard
        max_sim = {}
        for item in comparison_matrix:
            u, c, j = item['user'], item['compared_with'], item.get('jaccard_index') or 0
            max_sim[u] = max(max_sim.get(u, 0), j)
            max_sim[c] = max(max_sim.get(c, 0), j)

        sorted_users = sorted(max_sim.items(), key=lambda x: x[1], reverse=True)
        top_users = [uid for uid, _ in sorted_users[:top_n]]
        
        lookup = {}
        for item in comparison_matrix:
            j = item.get('jaccard_index') or 0
            lookup[(item['user'], item['compared_with'])] = j
            lookup[(item['compared_with'], item['user'])] = j

        n = len(top_users)
        matrix = np.zeros((n, n))
        for i, u1 in enumerate(top_users):
            for j, u2 in enumerate(top_users):
                matrix[i][j] = 1.0 if u1 == u2 else lookup.get((u1, u2), 0)

        labels = [f'U{uid}' for uid in top_users]

        fig, ax = plt.subplots(figsize=(22, 18))
        im = ax.imshow(matrix, cmap='Reds', vmin=0, vmax=1, aspect='auto')

        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=19)
        ax.set_yticklabels(labels, fontsize=19)

        for i in range(n):
            for j in range(n):
                val = matrix[i][j]
                color = 'white' if val > 0.5 else 'black'
                ax.text(j, i, f'{val:.2f}', ha='center', va='center', fontsize=15, color=color)

        ax.set_title(f'Heatmap de Similaridade Jaccard — Top {top_n} Suspeitos', fontsize=16, fontweight='bold')
        plt.tight_layout()

        filename = f'heatmap_{exam_id}.png'
        filepath = os.path.join(PUBLIC_DIR, filename)
        plt.savefig(filepath, dpi=120)
        plt.close(fig)

        return filename