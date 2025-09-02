from flask import Flask, redirect
from flasgger import Swagger

from src.routes import api
from src.config.config import Config

app = Flask(__name__)

config = Config().dev_config

app.env = config.ENV

app.config['SWAGGER'] = {
    'title': 'Detection Service API',
}
swagger = Swagger(app)

@app.route("/")
def root():
    return redirect("/api/")

app.register_blueprint(api, url_prefix="/api")
