from multiprocessing import Pool, cpu_count
from functools import partial
from flask import jsonify, request, Blueprint
from src.models.respostas_lake import RespostasLake
from src.services.users_service import UsersService
from src.services.comparasion_service import ComparisonService
from src.services.graph_service import GraphService

comparison = Blueprint("comparison", __name__)

@comparison.route('/compare', methods=['GET'])
def compare_similarity():
    from src import db

    exam_id = request.args.get('examId')
    source_id = request.args.get('sourceId')
    metric = request.args.get('metric', 'both')

    if metric not in ['jaccard', 'dl', 'both']:
        return jsonify({'error': 'Invalid metric. Must be "jaccard", "dl", or "both"'}), 400

    users = RespostasLake.select_users(exam_id, source_id)
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
        'total_collected': len(comparison_matrix)
    }

    if metric in ['jaccard', 'both']:
        jaccard_chart = GraphService.generate_similarity_chart(
            comparison_matrix,
            'jaccard_index',
            'Distribuição da Similaridade Jaccard',
            'jaccard_distribution.png'
        )
        response_data['jaccard_chart_file'] = jaccard_chart

        response_data['comparison_matrix'].extend([
            {
                'user': item['user'],
                'compared_with': item['compared_with'],
                'jaccard_index': item.get('jaccard_index'),
                'dl_similarity': item.get('dl_similarity'),
                'totalUser': len(item['user_resp']),
                'totalComparedUser': len(item['response_other'])
            }
            for item in sorted(
                comparison_matrix,
                key=lambda x: x.get('jaccard_index', 0),
                reverse=True
            )
        ])

    if metric in ['dl', 'both']:
        dl_chart = GraphService.generate_similarity_chart(
            comparison_matrix,
            'dl_similarity',
            'Distribuição da Similaridade Damerau-Levenshtein',
            'dl_distribution.png'
        )
        response_data['dl_chart_file'] = dl_chart

        if metric == 'dl':
            response_data['comparison_matrix'] = [
                {
                    'user': item['user'],
                    'compared_with': item['compared_with'],
                    'dl_similarity': item.get('dl_similarity'),
                    'totalUser': len(item['user_resp']),
                    'totalComparedUser': len(item['response_other'])
                }
                for item in sorted(
                    comparison_matrix,
                    key=lambda x: x.get('dl_similarity', 0),
                    reverse=True
                )
            ]

    # pylint: enable=no-value-for-parameter
    return jsonify(response_data)

@comparison.route('/', methods=['GET'])
def get_all_respostas():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])

@comparison.route('/no-timestamp', methods=['GET'])
def get_all_respostas_no_timestamp():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])
