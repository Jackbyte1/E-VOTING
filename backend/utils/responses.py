from flask import jsonify


def success(data=None, message="OK", status=200):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def error(message, status=400):
    return jsonify({"success": False, "message": message}), status
