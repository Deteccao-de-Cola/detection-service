from collections import Counter
import matplotlib.pyplot as plt
from src.models.respostas_lake import RespostasLake
from datetime import datetime

class DamerauLevenshteinService:
    
    @staticmethod
    def damerau_levenshtein_distance(seq1, seq2):
        list1 = sorted(list(seq1), key=lambda x: x[0])
        list2 = sorted(list(seq2), key=lambda x: x[0])
        
        len1 = len(list1)
        len2 = len(list2)
        
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j
        
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if list1[i-1] == list2[j-1]:
                    cost = 0
                else:
                    cost = 1
                
                dp[i][j] = min(
                    dp[i-1][j] + 1,      
                    dp[i][j-1] + 1,      
                    dp[i-1][j-1] + cost 
                )
                
                if i > 1 and j > 1 and list1[i-1] == list2[j-2] and list1[i-2] == list2[j-1]:
                    dp[i][j] = min(dp[i][j], dp[i-2][j-2] + 1)
        
        return dp[len1][len2]

    @staticmethod
    def damerau_levenshtein_similarity(seq1, seq2):

        distance = DamerauLevenshteinService.damerau_levenshtein_distance(seq1, seq2)
        max_len = max(len(seq1), len(seq2))
        
        if max_len == 0:
            return 1.0
        
        return 1 - (distance / max_len)
