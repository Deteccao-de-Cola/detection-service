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
from src.services.heatmap_service import HeatmapService
from src.services.analytics_service import AnalyticsService
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

    contest_info = QuestionLevelService.recalculate_questions_level(exam_id)

    users = RespostasLake.select_users(exam_id, sourceId)
    user_metadata = RespostasLake.get_user_exam_metadata(exam_id) if exam_id is not None else {}

    with_timestamp = RespostasLake.get_salvar_tempo_resposta(exam_id) if exam_id is not None else True
    responses_cache = {
        uid: RespostasLake.select_user_questions(uid, exam_id, withTimestamp=with_timestamp)
        for uid in users
    }

    db.engine.dispose()

    num_processes = cpu_count()

    # pylint: disable=no-value-for-parameter
    user_batches = UsersService.create_batches(users, num_processes)
    process_func = partial(ComparisonService.process_user_batch,
                          all_users=users,
                          exam_id=exam_id,
                          responses_cache=responses_cache,
                          with_timestamp=with_timestamp)

    with Pool(processes=num_processes, initializer=ComparisonService.init_worker) as pool:
        results = pool.map(process_func, user_batches)

    comparison_matrix = [item for batch in results for item in batch]

    for item in comparison_matrix:
        item['user_aplicacoes'] = user_metadata.get(item['user'], [])
        item['compared_aplicacoes'] = user_metadata.get(item['compared_with'], [])

    response_data = {
        'comparison_matrix': [],
        'total_collected': len(comparison_matrix),
        'contest_info': contest_info
    }

    response_data['comparison_matrix'].extend([
        {
            'user': item['user'],
            'compared_with': item['compared_with'],
            'lev_similarity': item.get('lev_similarity'),
            'jaccard_index': item.get('jaccard_index'),
            'dl_similarity': item.get('dl_similarity'),
            'dl_operations': item.get('dl_operations'),
            'totalUser': len(item['user_resp']),
            'totalComparedUser': len(item['response_other']),
            'time_result_diff': item.get('time_result_diff'),
            'user_1_avarage_time': item.get('user_1_avarage_time'),
            'user_2_avarage_time': item.get('user_2_avarage_time'),
            'user_aplicacoes': item.get('user_aplicacoes', []),
            'compared_aplicacoes': item.get('compared_aplicacoes', []),
        }
        for item in sorted(
            comparison_matrix,
            key=lambda x: x.get('jaccard_index', 0),
            reverse=True
        )
    ])

    
    heatmap_image = HeatmapService.generate_jaccard_heatmap(comparison_matrix, exam_id, top_n=25)
    response_data['heatmap_image'] = heatmap_image

    analytics = AnalyticsService.compute_chart_data(response_data['comparison_matrix'])
    response_data.update(analytics)

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
