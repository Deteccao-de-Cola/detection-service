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
    metric = ma.fields.Str(
        load_default='both',
        validate=validate.OneOf(['jaccard', 'dl', 'both']),
        metadata={"description": "Similarity metric: 'jaccard', 'dl', or 'both'"}
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


class ComparisonItemSchema(ma.Schema):
    user = ma.fields.Raw()
    compared_with = ma.fields.Raw()
    jaccard_index = ma.fields.Float(allow_none=True)
    dl_similarity = ma.fields.Float(allow_none=True)
    dl_operations = ma.fields.Int(allow_none=True)
    totalUser = ma.fields.Int()
    totalComparedUser = ma.fields.Int()
    time_result_diff = ma.fields.Float(allow_none=True)
    user_1_avarage_time = ma.fields.Float(allow_none=True)
    user_2_avarage_time = ma.fields.Float(allow_none=True)


class JaccardComparisonResponseSchema(ma.Schema):
    comparison_matrix = ma.fields.List(ma.fields.Nested(JaccardComparisonItemSchema))
    total_collected = ma.fields.Int()


class DLComparisonResponseSchema(ma.Schema):
    comparison_matrix = ma.fields.List(ma.fields.Nested(DLComparisonItemSchema))
    total_collected = ma.fields.Int()


class QuestionInfoSchema(ma.Schema):
    idQuestao = ma.fields.Int()
    opcaoCorreta = ma.fields.Int(allow_none=True)
    nome = ma.fields.Str(allow_none=True)
    descricao = ma.fields.Str(allow_none=True)
    dificuldade = ma.fields.Str(allow_none=True)
    erradas = ma.fields.Int()
    corretas = ma.fields.Int()
    puladas = ma.fields.Int()
    percentualAcerto = ma.fields.Float()


class ComparisonResponseSchema(ma.Schema):
    comparison_matrix = ma.fields.List(ma.fields.Nested(ComparisonItemSchema))
    total_collected = ma.fields.Int()
    contest_info = ma.fields.List(ma.fields.Nested(QuestionInfoSchema))
