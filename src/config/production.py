# pylint: disable=invalid-name
class ProductionConfig:
    def __init__(self):
        self.ENV = "production"
        self.DEBUG = False
        self.PORT = 8000
        self.HOST = '0.0.0.0'
