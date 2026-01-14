from collections import Counter
import matplotlib.pyplot as plt
from datetime import datetime

class GraphService:
    @staticmethod
    def generate_similarity_chart(comparison_matrix, metric_key, title, filename):

        similarities = [item[metric_key] for item in comparison_matrix]

        def categorize_similarity(similarity):
            if similarity < 0.3:
                return '0.0 - 0.3 (Baixa)'
            if similarity < 0.5:
                return '0.3 - 0.5 (Média-Baixa)'
            if similarity < 0.7:
                return '0.5 - 0.7 (Média)'
            if similarity < 0.9:
                return '0.7 - 0.9 (Alta)'
            return '0.9 - 1.0 (Muito alta)'

        categories = [categorize_similarity(sim) for sim in similarities]
        category_counts = Counter(categories)

        ordered_labels = [
            '0.0 - 0.3 (Baixa)',
            '0.3 - 0.5 (Média-Baixa)',
            '0.5 - 0.7 (Média)',
            '0.7 - 0.9 (Alta)',
            '0.9 - 1.0 (Muito alta)'
        ]

        sizes = [category_counts.get(label, 0) for label in ordered_labels]
        colors = ['#ff9999', '#ffcc99', '#ffff99', '#99ff99', '#99ccff']

        plt.figure(figsize=(12, 7))
        bars = plt.bar(ordered_labels, sizes, color=colors, edgecolor='black', linewidth=1.2)

        for cur_bar in bars:
            height = cur_bar.get_height()
            plt.text(cur_bar.get_x() + cur_bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

        plt.xlabel('Faixa de Similaridade', fontsize=12, fontweight='bold')
        plt.ylabel('Número de Comparações', fontsize=12, fontweight='bold')
        plt.title(title, fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3, linestyle='--')

        plt.tight_layout()
        plt.savefig("src/public/" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + filename, 
                    dpi=300, bbox_inches='tight')
        plt.close()

        return filename