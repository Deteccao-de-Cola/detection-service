# pylint: disable=duplicate-code
# Controllers share similar structure for each similarity metric endpoint.
# Intentional duplication to maintain separation of concerns per algorithm.
from multiprocessing import Pool, cpu_count
from functools import partial
from flask_smorest import Blueprint
from src.models.respostas_lake import RespostasLake
from src.services.users_service import UsersService
from src.services.comparasion_service import ComparisonService
from src.services.question_level_service import QuestionLevelService
from src.schemas import (
    CompareWithMetricQuerySchema,
    ComparisonResponseSchema,
    RespostaSchema,
)

comparison = Blueprint("comparison", __name__, description="Combined similarity comparison endpoints")


@comparison.route('/compare', methods=['GET'])
@comparison.arguments(CompareWithMetricQuerySchema, location='query')
@comparison.response(200, ComparisonResponseSchema)
def compare_similarity(query_args):
    # pylint: disable=import-outside-toplevel
    from src import db

    exam_id = query_args.get('examId')
    sourceId = query_args.get('sourceId')
    metric = query_args.get('metric', 'both')

    contest_info = QuestionLevelService.recalculate_questions_level(exam_id)

    users = RespostasLake.select_users(exam_id, sourceId)
    db.engine.dispose()

    num_processes = cpu_count()

    # pylint: disable=no-value-for-parameter
    user_batches = UsersService.create_batches(users, num_processes)
    process_func = partial(ComparisonService.process_user_batch,
                          all_users=users,
                          exam_id=exam_id,
                          metrics=metric)

    with Pool(processes=num_processes, initializer=ComparisonService.init_worker) as pool:
        results = pool.map(process_func, user_batches)

    comparison_matrix = [item for batch in results for item in batch]

    response_data = {
        'comparison_matrix': [],
        'total_collected': len(comparison_matrix),
        'contest_info': contest_info
    }

    if metric in ['jaccard', 'both']:
        response_data['comparison_matrix'].extend([
            {
                'user': item['user'],
                'compared_with': item['compared_with'],
                'jaccard_index': item.get('jaccard_index'),
                'dl_similarity': item.get('dl_similarity'),
                'dl_operations': item.get('dl_operations'),
                'totalUser': len(item['user_resp']),
                'totalComparedUser': len(item['response_other']),
                'time_result_diff': item.get('time_result_diff'),
                'user_1_avarage_time': item.get('user_1_avarage_time'),
                'user_2_avarage_time': item.get('user_2_avarage_time'),
            }
            for item in sorted(
                comparison_matrix,
                key=lambda x: x.get('jaccard_index', 0),
                reverse=True
            )
        ])

    if metric == 'dl':
        response_data['comparison_matrix'] = [
            {
                'user': item['user'],
                'compared_with': item['compared_with'],
                'dl_similarity': item.get('dl_similarity'),
                'dl_operations': item.get('dl_operations'),
                'totalUser': len(item['user_resp']),
                'totalComparedUser': len(item['response_other']),
                'time_result_diff': item.get('time_result_diff'),
                'user_1_avarage_time': item.get('user_1_avarage_time'),
                'user_2_avarage_time': item.get('user_2_avarage_time'),
            }
            for item in sorted(
                comparison_matrix,
                key=lambda x: x.get('dl_similarity', 0),
                reverse=True
            )
        ]

    # pylint: enable=no-value-for-parameter
    return response_data


@comparison.route('/', methods=['GET'])
@comparison.response(200, RespostaSchema(many=True))
def get_all_respostas():
    return RespostasLake.query.all()


@comparison.route('/no-timestamp', methods=['GET'])
@comparison.response(200, RespostaSchema(many=True))
def get_all_respostas_no_timestamp():
    return RespostasLake.query.all()
