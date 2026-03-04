from flask_smorest import Blueprint
from src.schemas import HealthSchema

home = Blueprint("home", __name__, description="Home endpoints")


@home.route('/', methods=["GET"])
@home.response(200, HealthSchema)
def hello():
    return {'status': 'success', 'message': 'Detection Service on Production!'}


@home.route('health', methods=["GET"])
@home.response(200, HealthSchema)
def health():
    return {'status': 'success', 'message': 'Detection Service health!'}
