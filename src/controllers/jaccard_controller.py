from flask import Flask, jsonify, request, Blueprint
from src.models.respostas_lake import db, RespostasLake
from src.services.users_service import *
from src.services.jaccard_service import *
from multiprocessing import Pool, cpu_count
from functools import partial
import numpy as np

jaccard = Blueprint("jaccard", __name__)


'''
    Queries importantes:
    -- Conta o número de usuários distintos na base: SELECT COUNT(DISTINCT(user_id)) FROM tccunb.respostas;
    -- Para cada um dos usuários seleciona o worker e faz a comparação de acordo com as questões que o usuário de index tiver
    -- For each (usuário)
        - Filtra para possuir apenas as informações importantes 
        - Compare as questões respondidas com os outros usuários do sitema
        - Para cada usuário coletar as questões e comparar com uma função de comparação
        - Se existir alguma pergunta para um usuário, então devo armazenar a pessoa em uma matriz 
        - A partir da análize da cada usuário será gerado uma matriz com o índice de similiaridade dos usuários. 
        - Essa matriz deverá ser exibida para os usuários (HEATMAP) 
'''

'''
    2 Tipos de abordagens
    1 - Analize realizada com foco nos usuários
    2 - Analize realizada com foco nas questões e a parti dela pegar os usuários que estão colando nas provas.

    Consequências:
    No mundo real a idéia é comparar as questões a partir dos usuários e das respostas dos usuários, não das questões mais respondidas
    No caso seria interessante analizar os dois caminhos na verdade, mas prioritáriamente analizar por usuário.     
'''

''' 
    Preciso de processar os json's
    1 - Pega do banco de dados os dados de todos os usuários 
    2 - Para cada usuário gerar uma lista encadeada de quetões realizadas
    3 - A partir desta lista fazer a comparação com todos os usuários que possuem as mesma questão respondida
    4 - Fazer análize dessas questões, utilizando de workers para dividir cada um dos usuários e fazer a comparação entre eles 
'''
'''
    Outra abordagem que pode ser utiliada é:
    1 - Coletar as 100 questões mais respondidas
    2 - Utilizar essas questões como base para fazer a análize 
    3 - 
'''

@jaccard.route('/compare', methods=['GET'])
def compare_with_jaccard():
    users = RespostasLake.select_users()
    
    num_processes = cpu_count()
    
    user_batches = UsersService.create_batches(users, num_processes)
    process_func = partial(JaccardService.process_user_batch, all_users=users, index_min=0.3)
    
    with Pool(processes=num_processes, initializer=JaccardService.init_worker) as pool:
        results = pool.map(process_func, user_batches)

    comparison_matrix = [item for batch in results for item in batch]
    chart_filename = JaccardService.generate_jaccard_pie_chart(comparison_matrix)

    return jsonify({
        'chart_filename': chart_filename,
        'comparison_matrix': [{'user' : item['user'], 'compared_with': item['compared_with'], 'jaccard_index': item['jaccard_index']} for item in sorted(comparison_matrix, key=lambda x: x['jaccard_index'], reverse=True)[:15]],
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






    