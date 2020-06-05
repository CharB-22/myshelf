from functools import wraps
from flask import g, request, redirect, url_for, session

"""Decorate routes to require login. http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/ """
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("login")
        return f(*args, **kwargs)
    return decorated_function