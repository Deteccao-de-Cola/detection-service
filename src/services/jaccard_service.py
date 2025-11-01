'''
1 - Extract the context id, answer, and time
2 - Compare extracted content with jaccard
'''

class JaccardService:
    '''
        Function to compare questions
        1 - Clear the array, to only send to Jaccard the questions that are mutal in both arrays
    '''
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

        return JaccardService.jaccard_index(user1_responses, user2_responses)

    '''
        Function to define jaccard index

    def jaccard_similarity(set1, set2):
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0

      J(A, B) = |A ^ B| / |A u B|
    - |A ^ B| é o número de elementos em comum (Interseção).
    - |A u B| é o número total de elementos únicos (União).
    '''
    @staticmethod
    def jaccard_index(set1,set2):
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if not union > 0:
            return 0

        return intersection / union
