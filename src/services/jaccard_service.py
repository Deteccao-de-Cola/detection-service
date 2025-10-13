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
        
        list2_dict = {item['item_id']: (item['user_id'], item['resposta_usuario'])  for item in contest_to_be_compared}
        user1_responses = set()
        user2_responses = set()

        for item in contest:
            item_id = item['item_id']
            
            if item_id in list2_dict:
                user1_responses.add((item['user_id'], item['resposta_usuario']))
                user2_responses.add((list2_dict[item_id][0], list2_dict[item_id][1]))

        index = JaccardService.jaccardIndex(user1_responses, user2_responses)
        print(index)
    
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
        print(set1, "us2" ,set2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        #print(set1, set2)
        if not (union > 0):
            return 0
            
        return intersection / union 
