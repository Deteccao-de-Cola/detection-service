import os

from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.environ.get('MYSQL_HOST', 'db-tcc-cola')
MYSQL_USER = os.environ.get('MYSQL_USER', 'user')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'mysqlPass')
MYSQL_DB = os.environ.get('MYSQL_DB', 'tccdb')
MYSQL_PORT = int(os.environ.get('MYSQL_PORT', '3306'))
