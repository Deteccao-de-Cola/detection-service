from src.controllers.home_controller import home
from src.controllers.respostas_controller import respostas
from src.controllers.jaccard_controller import jaccard
from src.controllers.damerau_levenshtein_controller import damerau_levenshtein
from src.controllers.comparison_controller import comparison

blueprints = [
    (home, "/api/"),
    (respostas, "/api/respostas"),
    (jaccard, "/api/jaccard"),
    (damerau_levenshtein, "/api/damerau_levenshtein"),
    (comparison, "/api/comparison"),
]
