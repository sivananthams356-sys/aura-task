"""Standard response helpers: success envelope, error envelope, pagination."""
from flask import jsonify, request


class ApiError(Exception):
    def __init__(self, status, code, message, details=None):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def error_response(status, code, message, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def ok(data, status=200, meta=None):
    body = {"data": data}
    if meta is not None:
        body["meta"] = meta
    return jsonify(body), status


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "BAD_REQUEST", "Request body must be a JSON object")
    return data


def _page_args():
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = min(max(request.args.get("per_page", 20, type=int) or 20, 1), 100)
    return page, per_page


def paginate(query, serialize):
    page, per_page = _page_args()
    p = query.paginate(page=page, per_page=per_page, error_out=False)
    return ok([serialize(i) for i in p.items],
              meta={"page": page, "per_page": per_page, "total": p.total, "pages": p.pages})


def paginate_list(items):
    """Paginate a plain Python list of already-serialised items."""
    page, per_page = _page_args()
    total = len(items)
    pages = (total + per_page - 1) // per_page
    start = (page - 1) * per_page
    return ok(items[start:start + per_page],
              meta={"page": page, "per_page": per_page, "total": total, "pages": pages})
