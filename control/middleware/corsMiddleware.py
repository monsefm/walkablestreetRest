class corsMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Headers"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS, DELETE, PATCH"
        return response

    def process_response(self, req, resp):
        resp["Access-Control-Allow-Origin"] = "*"
        resp["Access-Control-Allow-Headers"] = "*"
        resp["Access-Control-Allow-Methods"] = "GET, POST, PUT, OPTIONS, DELETE, PATCH"
        return resp
