import os
from flask import Flask, redirect, send_from_directory
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from flask_mysqldb import MySQL
from src.config.config import Config
from src.models.respostas_lake import db, RespostasLake

app = Flask(__name__)

MYSQL_HOST = 'db-tcc-cola'
MYSQL_USER = 'user'
MYSQL_PASSWORD = 'mysqlPass'
MYSQL_DB = 'tccdb'
MYSQL_PORT = 3306


app.config['SQLALCHEMY_DATABASE_URI'] = (
    f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}'
    f'@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['API_TITLE'] = 'Detection Service API'
app.config['API_VERSION'] = 'v1'
app.config['OPENAPI_VERSION'] = '3.0.3'
app.config['OPENAPI_URL_PREFIX'] = '/'
app.config['OPENAPI_SWAGGER_UI_PATH'] = '/swagger-ui'
app.config['OPENAPI_SWAGGER_UI_URL'] = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/'

db.init_app(app)

config = Config().dev_config
app.env = config.ENV

smorest_api = Api(app)

@app.route("/")
def root():
    return redirect("/swagger-ui")

@app.route("/health")
def health():
    return {"status": "healthy"}, 200

@app.route('/public/<path:filename>')
def serve_public(filename):
    public_folder = os.path.join(app.root_path, 'public')
    return send_from_directory(public_folder, filename)

from src.routes import blueprints  # noqa: E402
for blp, prefix in blueprints:
    smorest_api.register_blueprint(blp, url_prefix=prefix)
