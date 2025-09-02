from flask import Flask, redirect
from flask_swagger_ui import get_swaggerui_blueprint

from src.routes import api
from src.config.config import Config

app = Flask(__name__)

config = Config().dev_config

app.env = config.ENV

@app.route("/")
def root():
    return redirect("/api/")

SWAGGER_URL = '/api/docs'
API_URL = 'http://127.0.0.1:8000/'  # Our API url (can of course be a local resource)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "Detection Service API"
    },
)

app.register_blueprint(api, url_prefix="/api")
app.register_blueprint(swaggerui_blueprint)
