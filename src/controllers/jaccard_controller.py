from multiprocessing import Pool, cpu_count
from functools import partial
from flask import jsonify, request, Blueprint
from src.models.respostas_lake import RespostasLake
from src.services.users_service import UsersService
from src.services.comparasion_service import ComparisonService
from src.services.graph_service import GraphService

jaccard = Blueprint("jaccard", __name__)

'''
    Queries importantes:
    -- Conta o número de usuários distintos na base:
        SELECT COUNT(DISTINCT(user_id)) FROM tccunb.respostas;
    -- Para cada um dos usuários seleciona o worker e faz a comparação de
        acordo com as questões que o usuário de index tiver
    -- For each (usuário)
        - Filtra para possuir apenas as informações importantes
        - Compare as questões respondidas com os outros usuários do sitema
        - Para cada usuário coletar as questões e comparar com uma função de
            comparação
        - Se existir alguma pergunta para um usuário, então devo armazenar a
            pessoa em uma matriz
        - A partir da análize da cada usuário será gerado uma matriz com o
            índice de similiaridade dos usuários.
        - Essa matriz deverá ser exibida para os usuários (HEATMAP)

    2 Tipos de abordagens
    1 - Analize realizada com foco nos usuários
    2 - Analize realizada com foco nas questões e a parti dela pegar os usuários
        que estão colando nas provas.

    Consequências:
    No mundo real a idéia é comparar as questões a partir dos usuários e das
        respostas dos usuários, não das questões mais respondidas
    No caso seria interessante analizar os dois caminhos na verdade, mas
        prioritáriamente analizar por usuário.

    Preciso de processar os json's
    1 - Pega do banco de dados os dados de todos os usuários
    2 - Para cada usuário gerar uma lista encadeada de quetões realizadas
    3 - A partir desta lista fazer a comparação com todos os usuários que
        possuem as mesma questão respondida
    4 - Fazer análize dessas questões, utilizando de workers para dividir cada
        um dos usuários e fazer a comparação entre eles

    Outra abordagem que pode ser utiliada é:
    1 - Coletar as 100 questões mais respondidas
    2 - Utilizar essas questões como base para fazer a análize
    3 -
'''
@jaccard.route('/compare', methods=['GET'])
def compare_with_jaccard():
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
                          metrics='jaccard')

    with Pool(processes=num_processes, initializer=ComparisonService.init_worker) as pool:
        results = pool.map(process_func, user_batches)

    comparison_matrix = [item for batch in results for item in batch]
    chart_filename = GraphService.generate_similarity_chart(comparison_matrix,
                                                             'jaccard_index',
                                                             'Distribuição da Similaridade Jaccard',
                                                             'jaccard_distribution.png')
    # pylint: enable=no-value-for-parameter
    return jsonify({
        'chart_file': chart_filename,
        'comparison_matrix': (
            [
                {'user' : item['user'],
                'compared_with': item['compared_with'],
                'jaccard_index': item['jaccard_index'],
                'totalUser' : len(item['user_resp']),
                'totalComparedUser' : len(item['response_other'], )}
                  for item in sorted(
                    comparison_matrix,
                    key=lambda x: x['jaccard_index'],
                    reverse=True)[:15]]
                ),
        'total_collected': len(comparison_matrix)
    })

@jaccard.route('/', methods=['GET'])
def get_all_respostas():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])

@jaccard.route('/no-timestamp', methods=['GET'])
def get_all_respostas_no_timestamp():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])
