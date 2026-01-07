import os
from flask import Flask, redirect, send_from_directory
from flasgger import Swagger
from flask_sqlalchemy import SQLAlchemy
from flask_mysqldb import MySQL
from src.routes import api
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

db.init_app(app)

config = Config().dev_config

app.env = config.ENV

app.config['SWAGGER'] = {
    'title': 'Detection Service API',
}
swagger = Swagger(app)

@app.route("/")
def root():
    return redirect("/api/")

@app.route('/public/<path:filename>')
def serve_public(filename):
    public_folder = os.path.join(app.root_path, 'public')
    return send_from_directory(public_folder, filename)

app.register_blueprint(api, url_prefix="/api")
