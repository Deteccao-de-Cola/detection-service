# pylint: disable=duplicate-code
from multiprocessing import Pool, cpu_count
from functools import partial
from flask_smorest import Blueprint
from src.models.respostas_lake import RespostasLake
from src.services.users_service import UsersService
from src.services.comparasion_service import ComparisonService
from src.schemas import (
    CompareQuerySchema,
    JaccardComparisonResponseSchema,
    RespostaSchema,
)

jaccard = Blueprint("jaccard", __name__, description="Jaccard similarity endpoints")


@jaccard.route('/compare', methods=['GET'])
@jaccard.arguments(CompareQuerySchema, location='query')
@jaccard.response(200, JaccardComparisonResponseSchema)
def compare_with_jaccard(query_args):
    # pylint: disable=import-outside-toplevel
    from src import db

    exam_id = query_args.get('examId')
    sourceId = query_args.get('sourceId')
    users = RespostasLake.select_users(exam_id, sourceId)
    db.engine.dispose()

    num_processes = cpu_count()
    # pylint: disable=no-value-for-parameter
    user_batches = UsersService.create_batches(users, num_processes)
    process_func = partial(ComparisonService.process_user_batch,
                          all_users=users,
                          exam_id=exam_id,
                          metrics='jaccard')

    with Pool(processes=num_processes, initializer=ComparisonService.init_worker) as pool:
        results = pool.map(process_func, user_batches)

    comparison_matrix = [item for batch in results for item in batch]

    # pylint: enable=no-value-for-parameter
    return {
        'comparison_matrix': [
            {
                'user': item['user'],
                'compared_with': item['compared_with'],
                'jaccard_index': item['jaccard_index'],
                'totalUser': len(item['user_resp']),
                'totalComparedUser': len(item['response_other']),
            }
            for item in sorted(
                comparison_matrix,
                key=lambda x: x['jaccard_index'],
                reverse=True,
            )
        ],
        'total_collected': len(comparison_matrix),
    }


@jaccard.route('/', methods=['GET'])
@jaccard.response(200, RespostaSchema(many=True))
def get_all_respostas():
    return RespostasLake.query.all()


@jaccard.route('/no-timestamp', methods=['GET'])
@jaccard.response(200, RespostaSchema(many=True))
def get_all_respostas_no_timestamp():
    return RespostasLake.query.all()
