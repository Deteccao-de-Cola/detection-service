from flask import Flask, jsonify, request, Blueprint
from src.models.respostas_lake import db, RespostasLake

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
    batch = 200; 
    users = RespostasLake.select_users()


    for user in users:
        current_user_response = RespostasLake.select_user_questions(user) 
        for other_users in users:
            if(other_users == user):
                continue
            
            respostas = RespostasLake.select_user_questions(other_users)
            print("Respostas:")
            print([other_users,respostas])
        
    return jsonify(users)

@jaccard.route('/', methods=['GET'])
def get_all_respostas():
    
    respostas = RespostasLake.query.all()

    
    return jsonify([r.to_dict() for r in respostas])



@jaccard.route('/no-timestamp', methods=['GET'])
def get_all_respostas_no_timestamp():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])






    