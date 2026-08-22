import itertools
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

MAX_DIFF_QUESTOES = 2

LIMIARES = [0.90, 0.98]

FAIXAS = [
    ("0-15s", 0, 15),
    ("15-30s", 15, 30),
    ("30-60s", 30, 60),
    ("1-3 min", 60, 180),
    ("3-5 min", 180, 300),
    ("5-10 min", 300, 600),
    ("10-30 min", 600, 1800),
    ("30+ min", 1800, None),
]

CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "public", "cache", "entrega_jaccard.json"
)

class EntregaJaccardService:

    @staticmethod
    def jaccard_index(set1, set2):
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0

    @staticmethod
    def _calcular_jaccard(respostas_aluno1, respostas_aluno2):
        todos_itens = set(respostas_aluno1.keys()) | set(respostas_aluno2.keys())
        conjunto1 = {(item, respostas_aluno1.get(item)) for item in todos_itens}
        conjunto2 = {(item, respostas_aluno2.get(item)) for item in todos_itens}
        return EntregaJaccardService.jaccard_index(conjunto1, conjunto2)

    @staticmethod
    def _faixa_para_diferenca(diff_segundos):
        for nome, minimo, maximo in FAIXAS:
            if maximo is None:
                if diff_segundos >= minimo:
                    return nome
            elif minimo <= diff_segundos < maximo:
                return nome
        raise ValueError(f"Diferença de tempo fora de faixa: {diff_segundos}")

    @staticmethod
    def _get_provas(db):
        rows = db.session.execute(db.text("SELECT idProva FROM PROVA ORDER BY idProva")).fetchall()
        return [row.idProva for row in rows]

    @staticmethod
    def _get_alunos_completos(db, id_prova):
        sql = """
            SELECT rp.cpf,
                   COUNT(DISTINCT ap.idAplicacao) AS aplicacoesRealizadas,
                   MAX(rp.dataHoraFim) AS entrega
            FROM realiza_prova AS rp
            INNER JOIN APLICACAO_PROVA AS ap ON ap.idAplicacao = rp.idAplicacao
            WHERE ap.idProva = :idProva
              AND rp.dataHoraFim IS NOT NULL
            GROUP BY rp.cpf
            HAVING aplicacoesRealizadas = (
                SELECT COUNT(*) FROM APLICACAO_PROVA WHERE idProva = :idProva
            )
        """
        rows = db.session.execute(db.text(sql), {"idProva": id_prova}).fetchall()
        return {row.cpf: row.entrega for row in rows}

    @staticmethod
    def _get_aplicacoes_por_aluno(db, id_prova):

        sql = """
            SELECT rp.cpf, area.sigla AS tipoProva, rp.dataHoraFim
            FROM realiza_prova AS rp
            INNER JOIN APLICACAO_PROVA AS ap ON ap.idAplicacao = rp.idAplicacao
            INNER JOIN AREA_CONHECIMENTO AS area ON area.idArea = ap.idArea
            WHERE ap.idProva = :idProva
              AND rp.dataHoraFim IS NOT NULL
        """
        rows = db.session.execute(db.text(sql), {"idProva": id_prova}).fetchall()

        aplicacoes_por_aluno = defaultdict(dict)
        for row in rows:
            aplicacoes_por_aluno[row.cpf][row.tipoProva] = row.dataHoraFim

        return aplicacoes_por_aluno

    @staticmethod
    def _avg_diff_segundos_par(aplicacoes_aluno1, aplicacoes_aluno2):
        diffs = []
        for tipo_prova, dt1 in aplicacoes_aluno1.items():
            dt2 = aplicacoes_aluno2.get(tipo_prova)
            if dt2 is None:
                continue
            diffs.append(abs((dt1 - dt2).total_seconds()))
        return sum(diffs) / len(diffs) if diffs else None

    @staticmethod
    def _get_respostas(db, id_prova):
        sql = """
            SELECT r.cpf, r.idQuestao AS itemId, r.resposta AS respostaUsuario,
                   r.dataHoraResposta, r.idResposta
            FROM RESPOSTA AS r
            INNER JOIN APLICACAO_PROVA AS ap ON ap.idAplicacao = r.idAplicacao
            WHERE ap.idProva = :idProva
        """
        rows = db.session.execute(db.text(sql), {"idProva": id_prova}).fetchall()

        escolhida = {}
        for row in rows:
            chave = (row.cpf, row.itemId)
            atual = escolhida.get(chave)
            if atual is None:
                escolhida[chave] = row
                continue

            ts_novo = row.dataHoraResposta
            ts_atual = atual.dataHoraResposta
            if ts_atual is None and ts_novo is not None:
                escolhida[chave] = row
            elif ts_novo is not None and ts_atual is not None and ts_novo >= ts_atual:
                escolhida[chave] = row
            elif ts_novo is None and ts_atual is None and row.idResposta >= atual.idResposta:
                escolhida[chave] = row

        respostas_por_aluno = defaultdict(dict)
        for (cpf, item_id), row in escolhida.items():
            respostas_por_aluno[cpf][item_id] = row.respostaUsuario

        return respostas_por_aluno

    @staticmethod
    def _processar_prova(db, id_prova):
        entregas = EntregaJaccardService._get_alunos_completos(db, id_prova)
        respostas = EntregaJaccardService._get_respostas(db, id_prova)
        aplicacoes_por_aluno = EntregaJaccardService._get_aplicacoes_por_aluno(db, id_prova)

        # só entram alunos que completaram as 3 aplicações E têm respostas registradas
        alunos = sorted(set(entregas.keys()) & set(respostas.keys()))

        pares = []
        descartados_diff_questoes = 0
        descartados_sem_area_casada = 0

        for cpf1, cpf2 in itertools.combinations(alunos, 2):
            r1 = respostas[cpf1]
            r2 = respostas[cpf2]

            if abs(len(r1) - len(r2)) > MAX_DIFF_QUESTOES:
                descartados_diff_questoes += 1
                continue

            # diferença de horário de entrega: mesmo cálculo já usado em produção
            # (AnalyticsService._avg_diff_minutes) — média das diferenças por área
            # casada (tipoProva), não o MAX agregado por aluno
            diff_segundos = EntregaJaccardService._avg_diff_segundos_par(
                aplicacoes_por_aluno[cpf1], aplicacoes_por_aluno[cpf2]
            )
            if diff_segundos is None:
                # não deveria acontecer — ambos completaram todas as aplicações,
                # então toda área de um tem correspondente no outro
                descartados_sem_area_casada += 1
                continue

            jaccard = EntregaJaccardService._calcular_jaccard(r1, r2)
            faixa = EntregaJaccardService._faixa_para_diferenca(diff_segundos)

            pares.append({"faixa": faixa, "jaccard": jaccard})

        return {
            "alunos_considerados": len(alunos),
            "pares": pares,
            "descartados_diff_questoes": descartados_diff_questoes,
            "descartados_sem_area_casada": descartados_sem_area_casada,
        }

    @staticmethod
    def _calcular(db):
        provas = EntregaJaccardService._get_provas(db)
        resultados_por_prova = [EntregaJaccardService._processar_prova(db, p) for p in provas]

        nomes_faixas = [nome for nome, _, _ in FAIXAS]

        total_por_faixa = {nf: 0 for nf in nomes_faixas}
        # acima_por_faixa[limiar][faixaTempo] = quantidade de pares com jaccard >= limiar
        acima_por_faixa = {limiar: {nf: 0 for nf in nomes_faixas} for limiar in LIMIARES}
        total_pares = 0
        total_acima_geral = {limiar: 0 for limiar in LIMIARES}  # em toda a base, p/ taxaGeral

        for resultado in resultados_por_prova:
            for par in resultado["pares"]:
                faixa = par["faixa"]
                jaccard = par["jaccard"]
                total_por_faixa[faixa] += 1
                total_pares += 1
                for limiar in LIMIARES:
                    if jaccard >= limiar:
                        acima_por_faixa[limiar][faixa] += 1
                        total_acima_geral[limiar] += 1

        # cada série (uma por limiar) traz, por faixa de tempo: total de pares,
        # pares acima do limiar e o percentual — nunca o percentual sozinho
        series = []
        tabela = []
        for limiar in LIMIARES:
            taxa_geral = round((total_acima_geral[limiar] / total_pares * 100), 2) if total_pares > 0 else 0
            acima_lista = []
            percentuais = []
            for nf in nomes_faixas:
                total_faixa = total_por_faixa[nf]
                acima = acima_por_faixa[limiar][nf]
                percentual = round((acima / total_faixa * 100), 2) if total_faixa > 0 else 0
                acima_lista.append(acima)
                percentuais.append(percentual)
                tabela.append({
                    "faixaTempo": nf,
                    "limiar": limiar,
                    "totalPares": total_faixa,
                    "paresAcimaDoLimiar": acima,
                    "percentual": percentual,
                })

            series.append({
                "limiar": limiar,
                "label": f"Jaccard ≥ {limiar:.2f}",
                "acimaDoLimiar": acima_lista,
                "percentuais": percentuais,
                "taxaGeral": taxa_geral,
                "totalAcimaDoLimiarGeral": total_acima_geral[limiar],
            })

        diagnostico = {
            "provasProcessadas": len(resultados_por_prova),
            "alunosConsiderados": sum(r["alunos_considerados"] for r in resultados_por_prova),
            "totalPares": total_pares,
            "descartadosDiffQuestoes": sum(r["descartados_diff_questoes"] for r in resultados_por_prova),
            "descartadosSemAreaCasada": sum(r["descartados_sem_area_casada"] for r in resultados_por_prova),
            "paresPorFaixa": total_por_faixa,
            "paresAcimaDoLimiarGeral": {str(limiar): total_acima_geral[limiar] for limiar in LIMIARES},
        }

        return {
            "faixasTempo": nomes_faixas,
            "totaisPorFaixa": [total_por_faixa[nf] for nf in nomes_faixas],
            "series": series,
            "tabela": tabela,
            "diagnostico": diagnostico,
            "calculadoEm": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _salvar_cache(resultado):
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

    @staticmethod
    def obter(db, forcar_recalculo=False):
        if not forcar_recalculo and os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)

        resultado = EntregaJaccardService._calcular(db)
        EntregaJaccardService._salvar_cache(resultado)
        return resultado
