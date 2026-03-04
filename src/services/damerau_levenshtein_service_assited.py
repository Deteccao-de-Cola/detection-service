class DamerauLevenshteinServiceAssisted:

    #Exemplo:
    #            col[0]   col[1]   col[2]   col[3]   col[4]
    #            guard      ""    (1,'A') (2,'X')  (3,'C')
    #row[0] grd:   6        6        6        6        6
    #row[1]  "":   6        0        1        2        3
    #row[2]  (A):  6        1        ?        ?        ?
    #row[3]  (B):  6        2        ?        ?        ?
    #row[4]  (C):  6        3        ?        ?        ?

    @staticmethod
    def damerau_levenshtein_distance(seq1, seq2):
        list1 = sorted(list(seq1), key=lambda x: x[0])
        list2 = sorted(list(seq2), key=lambda x: x[0])
        print("list1",list1)
        print("list2",list2)

        len1 = len(list1)
        len2 = len(list2)

        max_dist = len1 + len2
        
        d = [[0] * (len2 + 2) for _ in range (len1 + 2)] # Matrix row[0] * size of len2 
                                                         # Matrix create cols to each collumn * size of len1
        d[0][0] = max_dist # The max distance possible
        last_row_id = {}

        for i in range(len1 + 1): # De 0 a len1+1
            d[i+1][0] = max_dist # Pivot
            d[i+1][1] = i # Custo mínimo se houver operação

        for j in range(len2 + 1): # De 0 a len2+1; #Preenche as colunas com o custo mínimo
            d[0][j+1] = max_dist 
            d[1][j+1] = j   # Custo mínimo se houver operação

        for i in range(1, len1 + 1): # Realiza o loop de 
            last_col_id = 0

            for j in range(1, len2 + 1): 

                # Última linha onde o elemento atual de list2 apareceu em list1
                # (0 se nunca apareceu → transposição não vai disparar)
                i1 = last_row_id.get(list2[j-1], 0)

                # Última coluna onde o elemento atual de list1 apareceu em list2
                # (atualizado para j quando há match, reset para 0 a cada linha)
                j1 = last_col_id

                if list1[i-1] == list2[j-1]:
                    cost = 0        # mesma resposta → nenhuma operação
                    last_col_id = j # registra que list1[i-1] foi visto na coluna j
                else:
                    cost = 1        # respostas diferentes → operação necessária

                # Custo da transposição:
                #   d[i1][j1]        → custo acumulado até onde os dois elementos se cruzaram
                #   (i - i1 - 1)    → deletar os elementos de list1 entre i1 e i
                #   + 1             → o swap em si
                #   (j - j1 - 1)    → inserir os elementos de list2 entre j1 e j
                custo_transposicao = d[i1][j1] + (i - i1 - 1) + 1 + (j - j1 - 1)

                d[i+1][j+1] = min(
                    d[i][j]   + cost,           # match (0) ou substituição (1)
                    d[i+1][j] + 1,              # inserção: user2 tem resposta extra
                    d[i][j+1] + 1,              # deleção: user1 tem resposta extra
                    custo_transposicao          # transposição: respostas em ordem invertida
                )

            last_row_id[list1[i-1]] = i
        return d[len1+1][len2+1]
                



