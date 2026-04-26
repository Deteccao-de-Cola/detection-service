class HammingService:
    """
    Serviço de detecção de cola baseado na Distância de Hamming.

    A distância de Hamming conta o número de posições onde duas sequências
    diferem. Adaptada para comparar sequências de respostas de alunos,
    tratando posições ausentes como divergentes.
    """

    @staticmethod
    def hamming_distance(seq1, seq2):
        """
        Calcula a distância de Hamming entre duas sequências de respostas.
        Posições presentes em apenas uma das sequências são contadas como diferentes.
        Retorna o número inteiro de posições divergentes.
        """
        max_len = max(len(seq1), len(seq2)) if (seq1 or seq2) else 0
        count = 0
        for i in range(max_len):
            a = seq1[i] if i < len(seq1) else None
            b = seq2[i] if i < len(seq2) else None
            if a != b:
                count += 1
        return count

    @staticmethod
    def hamming_similarity(seq1, seq2):
        """
        Calcula a similaridade de Hamming normalizada entre 0 e 1.
        Similaridade 1.0 indica sequências idênticas.
        Similaridade 0.0 indica que todas as posições diferem.
        """
        max_len = max(len(seq1), len(seq2)) if (seq1 or seq2) else 0
        if max_len == 0:
            return 1.0
        distance = HammingService.hamming_distance(seq1, seq2)
        return 1 - (distance / max_len)
