import os
import json
from datetime import datetime, timezone

import numpy as np

from src.services.entrega_jaccard_service import (
    EntregaJaccardService,
    FAIXAS,
    LIMIARES,
    MAX_DIFF_QUESTOES,
)

# limites finitos das faixas de tempo, em segundos, na mesma ordem de FAIXAS —
# usados com np.digitize pra classificar as diferenças de horário embaralhadas
_LIMITES_FAIXAS_SEGUNDOS = [maximo for _, _, maximo in FAIXAS[:-1]]

N_PERMUTACOES_PADRAO = 2000
SEMENTE_PADRAO = 42

CACHE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "public", "cache", "entrega_jaccard_permutacao.json"
)


class PermutacaoEntregaService:

    @staticmethod
    def _preparar_prova(db, id_prova):

        entregas = EntregaJaccardService._get_alunos_completos(db, id_prova)
        respostas = EntregaJaccardService._get_respostas(db, id_prova)
        aplicacoes_por_aluno = EntregaJaccardService._get_aplicacoes_por_aluno(db, id_prova)

        alunos = sorted(set(entregas.keys()) & set(respostas.keys()))
        n = len(alunos)
        if n < 2:
            return None

        areas = sorted({tp for aplic in aplicacoes_por_aluno.values() for tp in aplic.keys()})
        if not areas:
            return None

        # matriz (n_alunos x n_areas) de horários em epoch-segundos; NaN onde
        # o aluno não tem entrega registrada naquela área
        tempos_matriz = np.full((n, len(areas)), np.nan, dtype=np.float64)
        for i, cpf in enumerate(alunos):
            aplic = aplicacoes_por_aluno.get(cpf, {})
            for a, area in enumerate(areas):
                dt = aplic.get(area)
                if dt is not None:
                    tempos_matriz[i, a] = dt.timestamp()

        idx_i, idx_j, jaccards = [], [], []
        for i in range(n):
            r1 = respostas[alunos[i]]
            for j in range(i + 1, n):
                r2 = respostas[alunos[j]]
                if abs(len(r1) - len(r2)) > MAX_DIFF_QUESTOES:
                    continue
                idx_i.append(i)
                idx_j.append(j)
                jaccards.append(EntregaJaccardService._calcular_jaccard(r1, r2))

        if not idx_i:
            return None

        return {
            "tempos_matriz": tempos_matriz,
            "idx_i": np.array(idx_i, dtype=np.int32),
            "idx_j": np.array(idx_j, dtype=np.int32),
            "jaccards": np.array(jaccards, dtype=np.float64),
        }

    @staticmethod
    def _tabular(tempos_matrizes, dados_provas, n_faixas):

        total = np.zeros(n_faixas, dtype=np.int64)
        acima = {limiar: np.zeros(n_faixas, dtype=np.int64) for limiar in LIMIARES}

        for d, matriz in zip(dados_provas, tempos_matrizes):
            diffs_por_area = np.abs(matriz[d["idx_i"], :] - matriz[d["idx_j"], :])
            with np.errstate(invalid="ignore"):
                diffs = np.nanmean(diffs_por_area, axis=1)
            buckets = np.digitize(diffs, _LIMITES_FAIXAS_SEGUNDOS)
            total += np.bincount(buckets, minlength=n_faixas)
            for limiar in LIMIARES:
                mask = d["jaccards"] >= limiar
                acima[limiar] += np.bincount(buckets[mask], minlength=n_faixas)

        return total, acima

    @staticmethod
    def _calcular(db, n_permutacoes=N_PERMUTACOES_PADRAO, semente=SEMENTE_PADRAO):
        provas = EntregaJaccardService._get_provas(db)
        dados_provas = [PermutacaoEntregaService._preparar_prova(db, p) for p in provas]
        dados_provas = [d for d in dados_provas if d is not None]

        nomes_faixas = [nome for nome, _, _ in FAIXAS]
        n_faixas = len(nomes_faixas)

        # observado (horários reais, sem embaralhar)
        matrizes_reais = [d["tempos_matriz"] for d in dados_provas]
        total_obs, acima_obs = PermutacaoEntregaService._tabular(matrizes_reais, dados_provas, n_faixas)

        # distribuição nula: embaralha as LINHAS da matriz dentro de cada
        # prova (o perfil de horários de um aluno nas 3 áreas se move
        # diferentes), recalcula as faixas com o Jaccard de cada par fixo
        rng = np.random.default_rng(semente)
        taxa_nula = {limiar: np.full((n_permutacoes, n_faixas), np.nan) for limiar in LIMIARES}

        for k in range(n_permutacoes):
            matrizes_embaralhadas = [rng.permutation(d["tempos_matriz"], axis=0) for d in dados_provas]
            total_k, acima_k = PermutacaoEntregaService._tabular(matrizes_embaralhadas, dados_provas, n_faixas)
            for limiar in LIMIARES:
                with np.errstate(divide="ignore", invalid="ignore"):
                    taxa_nula[limiar][k] = np.where(total_k > 0, acima_k[limiar] / total_k * 100, np.nan)

        resultados = []
        for fi, nome_faixa in enumerate(nomes_faixas):
            for limiar in LIMIARES:
                total_o = int(total_obs[fi])
                acima_o = int(acima_obs[limiar][fi])
                taxa_o = round((acima_o / total_o * 100), 4) if total_o > 0 else None

                taxas_k = taxa_nula[limiar][:, fi]
                taxas_validas = taxas_k[~np.isnan(taxas_k)]

                if len(taxas_validas) > 0 and taxa_o is not None:
                    media_nula = float(np.mean(taxas_validas))
                    desvio_nulo = float(np.std(taxas_validas))
                    # p-valor unicaudal com correção +1 (evita p=0 mesmo
                    # quando nenhuma permutação alcança a taxa observada)
                    extremos = int(np.sum(taxas_validas >= taxa_o))
                    p_valor = (extremos + 1) / (len(taxas_validas) + 1)
                else:
                    media_nula = None
                    desvio_nulo = None
                    p_valor = None

                resultados.append({
                    "faixaTempo": nome_faixa,
                    "limiar": limiar,
                    "observado": {
                        "totalPares": total_o,
                        "acimaDoLimiar": acima_o,
                        "taxa": round(taxa_o, 2) if taxa_o is not None else None,
                    },
                    "nulo": {
                        "mediaTaxa": round(media_nula, 4) if media_nula is not None else None,
                        "desvioPadraoTaxa": round(desvio_nulo, 4) if desvio_nulo is not None else None,
                        "permutacoesValidas": int(len(taxas_validas)),
                    },
                    "pValor": round(p_valor, 4) if p_valor is not None else None,
                })

        return {
            "permutacoes": n_permutacoes,
            "semente": semente,
            "resultados": resultados,
            "calculadoEm": datetime.now(timezone.utc).isoformat(),
        }

    @staticmethod
    def _salvar_cache(resultado):
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)

    @staticmethod
    def obter(db, forcar_recalculo=False, n_permutacoes=N_PERMUTACOES_PADRAO):
        if not forcar_recalculo and os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)

        resultado = PermutacaoEntregaService._calcular(db, n_permutacoes=n_permutacoes)
        PermutacaoEntregaService._salvar_cache(resultado)
        return resultado
