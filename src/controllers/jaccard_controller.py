from flask import Flask, jsonify, request, Blueprint
from src.models.respostas_lake import db, RespostasLake

jaccard = Blueprint("jaccard", __name__)

@jaccard.route('/', methods=['GET'])
def get_all_respostas():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])

@jaccard.route('/no-timestamp', methods=['GET'])
def get_all_respostas():
    respostas = RespostasLake.query.all()
    return jsonify([r.to_dict() for r in respostas])


