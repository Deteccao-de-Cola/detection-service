from multiprocessing import Pool, cpu_count
from functools import partial
from flask import jsonify, request, Blueprint
from src.models.respostas_lake import RespostasLake
from src.services.users_service import UsersService
from src.services.comparasion_service import ComparisonService
from src.services.graph_service import GraphService

damerau_levenshtein = Blueprint("damerau_levenshtein", __name__)

@damerau_levenshtein.route('/compare', methods=['GET'])
def compare_with_damerau_levenshtein():
    from src import db

    exam_id = request.args.get('examId')
    source_id = request.args.get('sourceId')
    users = RespostasLake.select_users(exam_id, source_id)
    db.engine.dispose()

    num_processes = cpu_count()
    # pylint: disable=no-value-for-parameter
    user_batches = UsersService.create_batches(users, num_processes)
    process_func = partial(ComparisonService.process_user_batch,
                          all_users=users,
                          exam_id=exam_id,
                          metrics='dl')

    with Pool(processes=num_processes, initializer=ComparisonService.init_worker) as pool:
        results = pool.map(process_func, user_batches)

    comparison_matrix = [item for batch in results for item in batch]
    chart_base64 = GraphService.generate_similarity_chart(comparison_matrix, 
                                                            'dl_similarity', 
                                                            'Distribuição da Similaridade Damerau-Levenshtein',
                                                            'dl_distribution.png')
    # pylint: enable=no-value-for-parameter
    return jsonify({
        'chart_file': chart_base64,
        'comparison_matrix': (
            [
                {'user' : item['user'],
                'compared_with': item['compared_with'],
                'dl_similarity': item['dl_similarity'],
                'totalUser' : len(item['user_resp']),
                'totalComparedUser' : len(item['response_other'], )}
                  for item in sorted(
                    comparison_matrix,
                    key=lambda x: x['dl_similarity'],
                    reverse=True)[:15]]
                ),
        'total_collected': len(comparison_matrix)
    })

@damerau_levenshtein.route('/', methods=['GET'])
def get_all_respostas():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])

@damerau_levenshtein.route('/no-timestamp', methods=['GET'])
def get_all_respostas_no_timestamp():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])
