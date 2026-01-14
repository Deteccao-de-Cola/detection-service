from flask import Blueprint
from src.controllers.home_controller import home
from src.controllers.respostas_controller import respostas
from src.controllers.jaccard_controller import jaccard
from src.controllers.damerau_levenshtein_controller import damerau_levenshtein
from src.controllers.comparison_controller import comparison

api = Blueprint('api', __name__)

api.register_blueprint(home, url_prefix="/")
api.register_blueprint(respostas, url_prefix="/respostas")
api.register_blueprint(jaccard, url_prefix="/jaccard")
api.register_blueprint(damerau_levenshtein, url_prefix="/damerau_levenshtein")
api.register_blueprint(comparison, url_prefix="/comparison")
