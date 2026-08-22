from flask_smorest import Blueprint
from src.services.entrega_jaccard_service import EntregaJaccardService
from src.services.permutacao_entrega_service import PermutacaoEntregaService
from src.schemas import (
    EntregaJaccardQuerySchema,
    EntregaJaccardResponseSchema,
    PermutacaoQuerySchema,
    PermutacaoResponseSchema,
)

entrega_jaccard = Blueprint(
    "entrega_jaccard", __name__,
    description="Relação entre diferença de horário de entrega e Índice de Jaccard, agregada entre todas as provas"
)


@entrega_jaccard.route('/', methods=['GET'])
@entrega_jaccard.arguments(EntregaJaccardQuerySchema, location='query')
@entrega_jaccard.response(200, EntregaJaccardResponseSchema)
def obter_entrega_jaccard(query_args):
    # pylint: disable=import-outside-toplevel
    from src import db

    resultado = EntregaJaccardService.obter(db, forcar_recalculo=query_args.get('force', False))
    db.engine.dispose()

    return resultado


@entrega_jaccard.route('/permutacao', methods=['GET'])
@entrega_jaccard.arguments(PermutacaoQuerySchema, location='query')
@entrega_jaccard.response(200, PermutacaoResponseSchema)
def obter_teste_permutacao(query_args):
    # pylint: disable=import-outside-toplevel
    from src import db

    resultado = PermutacaoEntregaService.obter(
        db,
        forcar_recalculo=query_args.get('force', False),
        n_permutacoes=query_args.get('permutacoes', 2000),
    )
    db.engine.dispose()

    return resultado
