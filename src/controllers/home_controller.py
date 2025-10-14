from flask import Response, json, Blueprint

home = Blueprint("home", __name__)

# route for api/
@home.route('/', methods = ["GET"])
def hello():
  return Response(
      response=json.dumps({
          'status': "success",
          "message": "Detection Service on Production!"
      }),
      status=200,
      mimetype='application/json'
  )
