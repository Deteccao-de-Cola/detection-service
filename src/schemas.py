import marshmallow as ma
from marshmallow import validate


class HealthSchema(ma.Schema):
    status = ma.fields.Str()
    message = ma.fields.Str()


class RespostaSchema(ma.Schema):
    id = ma.fields.Int()
    sourceId = ma.fields.Int()
    contestId = ma.fields.Int(allow_none=True)
    respondidaEm = ma.fields.DateTime(allow_none=True)
    itemId = ma.fields.Int()
    respostaUsuario = ma.fields.Str(allow_none=True)
    userId = ma.fields.Int()


class CompareQuerySchema(ma.Schema):
    examId = ma.fields.Str(
        load_default=None,
        metadata={"description": "Exam (contest) ID to filter by"}
    )
    sourceId = ma.fields.Str(
        load_default=None,
        metadata={"description": "Source ID to filter by"}
    )


class CompareWithMetricQuerySchema(ma.Schema):
    examId = ma.fields.Str(
        load_default=None,
        metadata={"description": "Exam (contest) ID to filter by"}
    )
    sourceId = ma.fields.Str(
        load_default=None,
        metadata={"description": "Source ID to filter by"}
    )


class JaccardComparisonItemSchema(ma.Schema):
    user = ma.fields.Raw()
    compared_with = ma.fields.Raw()
    jaccard_index = ma.fields.Float(allow_none=True)
    totalUser = ma.fields.Int()
    totalComparedUser = ma.fields.Int()


class DLComparisonItemSchema(ma.Schema):
    user = ma.fields.Raw()
    compared_with = ma.fields.Raw()
    dl_similarity = ma.fields.Float(allow_none=True)
    dl_operations = ma.fields.Int(allow_none=True)
    totalUser = ma.fields.Int()
    totalComparedUser = ma.fields.Int()


class AplicacaoMetadataSchema(ma.Schema):
    tipoProva = ma.fields.Str(allow_none=True)
    dataHoraFim = ma.fields.Str(allow_none=True)


class ComparisonItemSchema(ma.Schema):
    user = ma.fields.Raw()
    compared_with = ma.fields.Raw()
    jaccard_index = ma.fields.Float(allow_none=True)
    dl_similarity = ma.fields.Float(allow_none=True)
    dl_operations = ma.fields.Int(allow_none=True)
    hamming_similarity = ma.fields.Float(allow_none=True)
    totalUser = ma.fields.Int()
    totalComparedUser = ma.fields.Int()
    time_result_diff = ma.fields.Float(allow_none=True)
    user_1_avarage_time = ma.fields.Float(allow_none=True)
    user_2_avarage_time = ma.fields.Float(allow_none=True)
    user_aplicacoes = ma.fields.List(ma.fields.Nested(AplicacaoMetadataSchema), load_default=[])
    compared_aplicacoes = ma.fields.List(ma.fields.Nested(AplicacaoMetadataSchema), load_default=[])


class JaccardComparisonResponseSchema(ma.Schema):
    comparison_matrix = ma.fields.List(ma.fields.Nested(JaccardComparisonItemSchema))
    total_collected = ma.fields.Int()


class DLComparisonResponseSchema(ma.Schema):
    comparison_matrix = ma.fields.List(ma.fields.Nested(DLComparisonItemSchema))
    total_collected = ma.fields.Int()


class QuestionInfoSchema(ma.Schema):
    idQuestao = ma.fields.Int()
    nome = ma.fields.Str(allow_none=True)
    descricao = ma.fields.Str(allow_none=True)
    dificuldade = ma.fields.Str(allow_none=True)
    erradas = ma.fields.Int()
    corretas = ma.fields.Int()
    puladas = ma.fields.Int()
    percentualAcerto = ma.fields.Float()


class ImportacaoResponseSchema(ma.Schema):
    linhas_importadas = ma.fields.Int()
    mensagem = ma.fields.Str()


class EntregaJaccardQuerySchema(ma.Schema):
    force = ma.fields.Bool(
        load_default=False,
        metadata={"description": "Força o recálculo, ignorando o cache em disco"}
    )


class FaixaEntregaJaccardSchema(ma.Schema):
    faixaTempo = ma.fields.Str()
    limiar = ma.fields.Float()
    totalPares = ma.fields.Int()
    paresAcimaDoLimiar = ma.fields.Int()
    percentual = ma.fields.Float()


class DiagnosticoEntregaJaccardSchema(ma.Schema):
    provasProcessadas = ma.fields.Int()
    alunosConsiderados = ma.fields.Int()
    totalPares = ma.fields.Int()
    descartadosDiffQuestoes = ma.fields.Int()
    descartadosSemAreaCasada = ma.fields.Int()
    paresPorFaixa = ma.fields.Dict()
    paresAcimaDoLimiarGeral = ma.fields.Dict()


class SerieEntregaJaccardSchema(ma.Schema):
    limiar = ma.fields.Float()
    label = ma.fields.Str()
    acimaDoLimiar = ma.fields.List(ma.fields.Int())
    percentuais = ma.fields.List(ma.fields.Float())
    taxaGeral = ma.fields.Float()
    totalAcimaDoLimiarGeral = ma.fields.Int()


class EntregaJaccardResponseSchema(ma.Schema):
    faixasTempo = ma.fields.List(ma.fields.Str())
    totaisPorFaixa = ma.fields.List(ma.fields.Int())
    series = ma.fields.List(ma.fields.Nested(SerieEntregaJaccardSchema))
    tabela = ma.fields.List(ma.fields.Nested(FaixaEntregaJaccardSchema))
    diagnostico = ma.fields.Nested(DiagnosticoEntregaJaccardSchema)
    calculadoEm = ma.fields.Str()


class PermutacaoQuerySchema(ma.Schema):
    force = ma.fields.Bool(
        load_default=False,
        metadata={"description": "Força o recálculo, ignorando o cache em disco"}
    )
    permutacoes = ma.fields.Int(
        load_default=2000,
        metadata={"description": "Número de permutações a rodar"}
    )


class ObservadoPermutacaoSchema(ma.Schema):
    totalPares = ma.fields.Int()
    acimaDoLimiar = ma.fields.Int()
    taxa = ma.fields.Float(allow_none=True)


class NuloPermutacaoSchema(ma.Schema):
    mediaTaxa = ma.fields.Float(allow_none=True)
    desvioPadraoTaxa = ma.fields.Float(allow_none=True)
    permutacoesValidas = ma.fields.Int()


class ResultadoPermutacaoSchema(ma.Schema):
    faixaTempo = ma.fields.Str()
    limiar = ma.fields.Float()
    observado = ma.fields.Nested(ObservadoPermutacaoSchema)
    nulo = ma.fields.Nested(NuloPermutacaoSchema)
    pValor = ma.fields.Float(allow_none=True)


class PermutacaoResponseSchema(ma.Schema):
    permutacoes = ma.fields.Int()
    semente = ma.fields.Int()
    resultados = ma.fields.List(ma.fields.Nested(ResultadoPermutacaoSchema))
    calculadoEm = ma.fields.Str()


class ComparisonResponseSchema(ma.Schema):
    comparison_matrix = ma.fields.List(ma.fields.Nested(ComparisonItemSchema))
    total_collected = ma.fields.Int()
    contest_info = ma.fields.List(ma.fields.Nested(QuestionInfoSchema))
    heatmap_image = ma.fields.Str(allow_none=True)
    scatter_delivery_jaccard = ma.fields.List(ma.fields.Dict(), load_default=[])
    avg_delivery_all_pairs = ma.fields.Float(load_default=0)
    delivery_by_jaccard_range = ma.fields.List(ma.fields.Dict(), load_default=[])
    suspicion_table = ma.fields.List(ma.fields.Dict(), load_default=[])
    delivery_vs_avg = ma.fields.List(ma.fields.Dict(), load_default=[])
