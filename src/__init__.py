from flask import Flask, redirect
from flasgger import Swagger
from flask_sqlalchemy import SQLAlchemy
from flask_mysqldb import MySQL
import MySQLdb.cursors
from src.routes import api
from src.config.config import Config

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'your_username'
app.config['MYSQL_PASSWORD'] = 'your_password'
app.config['MYSQL_DB'] = 'your_database'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)

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
