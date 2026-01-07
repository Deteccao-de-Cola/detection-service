from flask import jsonify, Blueprint
from src.models.respostas_lake import db, RespostasLake

respostas = Blueprint("respostas", __name__)

@respostas.route('/', methods=['GET'])
def get_all_respostas():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])
