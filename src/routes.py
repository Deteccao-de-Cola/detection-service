from flask import Blueprint
from src.controllers.home_controller import home

api = Blueprint('api', __name__)

api.register_blueprint(home, url_prefix="/")
