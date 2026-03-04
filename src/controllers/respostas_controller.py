from flask_smorest import Blueprint
from src.models.respostas_lake import RespostasLake
from src.schemas import RespostaSchema

respostas = Blueprint("respostas", __name__, description="Respostas endpoints")


@respostas.route('/', methods=['GET'])
@respostas.response(200, RespostaSchema(many=True))
def get_all_respostas():
    return RespostasLake.query.all()
