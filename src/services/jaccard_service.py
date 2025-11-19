'''
1 - Extract the context id, answer, and time 
2 - Compare extracted content with jaccard
'''
from src.models.respostas_lake import db, RespostasLake
import matplotlib.pyplot as plt
from collections import Counter
import json

class JaccardService:
    def init_worker():
        from src import app, db 
        
        app.app_context().push()
        db.engine.dispose()
        
    @staticmethod
    def compare(contest, contest_to_be_compared):
        user1_dict = {item['item_id']: item['resposta_usuario'] for item in contest}
        user2_dict = {item['item_id']: item['resposta_usuario'] for item in contest_to_be_compared}
        
        all_items = set(user1_dict.keys()) | set(user2_dict.keys())
        
        user1_responses = set()
        user2_responses = set()
        for item_id in all_items:
            resp1 = user1_dict.get(item_id, None)
            user1_responses.add((item_id, resp1))
            
            resp2 = user2_dict.get(item_id, None)
            user2_responses.add((item_id, resp2))
        
        return JaccardService.jaccardIndex(user1_responses, user2_responses)
    
    @staticmethod
    def process_user_batch(user_batch, all_users, index_min):
        batch_results = []
        
        for user in user_batch:
            current_user_response = RespostasLake.select_user_questions(user)
            #if(len(current_user_response) > 3):
            for other_user in all_users:
                if other_user == user:
                    continue

                respostas_other_user = RespostasLake.select_user_questions(other_user)
                jaccard_result = JaccardService.compare(current_user_response, respostas_other_user)
                #print(user, other_user, len(current_user_response), len(respostas_other_user), jaccard_result)
                    
                if(jaccard_result > 0.01):
                    batch_results.append({
                        'user': user,
                        'compared_with': other_user,
                        'jaccard_index': jaccard_result,
                        'response_other': respostas_other_user,
                        'user_resp': current_user_response
                    })
        
        return batch_results

    
    '''
        Function to define jaccard index
    '''
    '''
    def jaccard_similarity(set1, set2):
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0
    
    '''

    '''
      J(A, B) = |A ^ B| / |A u B|
    - |A ^ B| é o número de elementos em comum (Interseção).
    - |A u B| é o número total de elementos únicos (União).
    '''
    @staticmethod
    def jaccardIndex(set1,set2):
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if not (union > 0):
            return 0
            
        return intersection / union 

    def generate_jaccard_pie_chart(comparison_matrix, filename='jaccard_distribution.png'):
        jaccard_indices = [item['jaccard_index'] for item in comparison_matrix]
        
        def categorize_index(index):
            if index < 0.3:
                return '0.0 - 0.3 (Baixa)'
            elif index < 0.5:
                return '0.3 - 0.5 (Média-Baixa)'
            elif index < 0.7:
                return '0.5 - 0.7 (Média)'
            elif index < 0.9:
                return '0.7 - 0.9 (Alta)'
            else:
                return '0.9 - 1.0 (Muito alta)'

        categories = [categorize_index(idx) for idx in jaccard_indices]
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

        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')

        plt.xlabel('Faixa de Similaridade', fontsize=12, fontweight='bold')
        plt.ylabel('Número de Comparações', fontsize=12, fontweight='bold')
        plt.title('Distribuição da Similaridade de Jaccard', fontsize=14, fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.grid(axis='y', alpha=0.3, linestyle='--')

        plt.tight_layout()
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        plt.close()

        
        return filename