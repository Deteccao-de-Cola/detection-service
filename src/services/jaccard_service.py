class JaccardService:
    # pylint: disable=pointless-string-statement
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
    # pylint: enable=pointless-string-statement
    @staticmethod
    def jaccard_index(set1,set2):
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))

        if not union > 0:
            return 0

        return intersection / union
