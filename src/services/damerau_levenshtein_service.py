class DamerauLevenshteinService:

    @staticmethod
    def damerau_levenshtein_distance(seq1, seq2):
        list1 = list(seq1)
        list2 = list(seq2)

        print("seq1 =>",seq1)
        print("seq2 =>", seq2)
        print("list1 =>",list1)
        print("list2 =>", list2)
        
        len1 = len(list1)
        len2 = len(list2)

        last_row_id = {}

        max_dist = len1 + len2
        d = [[0] * (len2 + 2) for _ in range(len1 + 2)]

        d[0][0] = max_dist
        for i in range(len1 + 1):
            d[i + 1][0] = max_dist
            d[i + 1][1] = i
        for j in range(len2 + 1):
            d[0][j + 1] = max_dist
            d[1][j + 1] = j

        for i in range(1, len1 + 1):
            last_col_id = 0

            for j in range(1, len2 + 1):
                i1 = last_row_id.get(list2[j - 1], 0)
                j1 = last_col_id

                if list1[i - 1] == list2[j - 1]:
                    cost = 0
                    last_col_id = j
                else:
                    cost = 1

                d[i + 1][j + 1] = min(
                    d[i][j] + cost,                                      # substitution / match
                    d[i + 1][j] + 1,                                     # insertion
                    d[i][j + 1] + 1,                                     # deletion
                    d[i1][j1] + (i - i1 - 1) + 1 + (j - j1 - 1),         # transposition
                )

            last_row_id[list1[i - 1]] = i

        return d[len1 + 1][len2 + 1]

    @staticmethod
    def damerau_levenshtein_similarity(seq1, seq2):

        distance = DamerauLevenshteinService.damerau_levenshtein_distance(seq1, seq2)
        max_len = max(len(seq1), len(seq2))

        if max_len == 0:
            return 1.0

        return 1 - (distance / max_len)

    @staticmethod
    def damerau_levenshtein_distance_any_swap(seq1, seq2):
        """
        Variante do DL onde qualquer transposição (adjacente ou não) custa 1.
        Diferença em relação ao DL padrão: remove a penalidade de gap na transposição.

        DL padrão:  d[i1][j1] + (i - i1 - 1) + 1 + (j - j1 - 1)  ← penaliza distância
        Esta versão: d[i1][j1] + 1                                  ← qualquer troca = 1

        Adequado para comparar ordens de resposta em provas: trocar Q6↔Q9
        deve custar o mesmo que trocar Q9↔Q10, independente da distância entre elas.
        """
        list1 = list(seq1)
        list2 = list(seq2)

        len1 = len(list1)
        len2 = len(list2)

        last_row_id = {}

        max_dist = len1 + len2
        d = [[0] * (len2 + 2) for _ in range(len1 + 2)]

        d[0][0] = max_dist
        for i in range(len1 + 1):
            d[i + 1][0] = max_dist
            d[i + 1][1] = i
        for j in range(len2 + 1):
            d[0][j + 1] = max_dist
            d[1][j + 1] = j

        for i in range(1, len1 + 1):
            last_col_id = 0

            for j in range(1, len2 + 1):
                i1 = last_row_id.get(list2[j - 1], 0)
                j1 = last_col_id

                if list1[i - 1] == list2[j - 1]:
                    cost = 0
                    last_col_id = j
                else:
                    cost = 1

                d[i + 1][j + 1] = min(
                    d[i][j] + cost,        # substituição / match
                    d[i + 1][j] + 1,       # inserção
                    d[i][j + 1] + 1,       # deleção
                    # d[i-1][j-1] + cost
                    d[i1][j1] + 1,         # qualquer transposição = custo 1
                )

                # if i > 1 and j > 1 and s1[i-1] == s2[j-2] and s1[i-2] == s2[j-1]:
                #     d[i][j] = min(d[i][j], d[i-2][j-2] + 1)

            last_row_id[list1[i - 1]] = i

        return d[len1 + 1][len2 + 1]

    @staticmethod
    def damerau_levenshtein_similarity_any_swap(seq1, seq2):
        distance = DamerauLevenshteinService.damerau_levenshtein_distance_any_swap(seq1, seq2)
        max_len = max(len(seq1), len(seq2))

        if max_len == 0:
            return 1.0, 0
        return 1 - (distance / max_len), distance
