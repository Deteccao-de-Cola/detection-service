from flask import Blueprint
from src.controllers.home_controller import home
from src.controllers.respostas_controller import respostas
from src.controllers.jaccard_controller import jaccard

api = Blueprint('api', __name__)

api.register_blueprint(home, url_prefix="/")
api.register_blueprint(respostas, url_prefix="/respostas")
api.register_blueprint(jaccard, url_prefix="/jaccard")
