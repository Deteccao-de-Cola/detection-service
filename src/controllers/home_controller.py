from flask import Response, json, Blueprint

home = Blueprint("home", __name__)

# route for api/
@home.route('/', methods = ["GET"])
def hello():
    """
    Hello endpoint
    ---
    tags:
      - Home
    responses:
      200:
        description: Returns a status and message
        schema:
          type: object
          properties:
            status:
              type: string
            message:
              type: string
    """
    return Response(
        response=json.dumps({
            'status': "success",
            "message": "Detection Service on Production!"
        }),
        status=200,
        mimetype='application/json'
    )
