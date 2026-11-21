"""鉴权：家长账号 session + 孩子 PIN session。"""
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
import hashlib


def hash_pwd(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()


def parent_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("parent"):
            if "/api/" in request.path:
                return jsonify(ok=False, code="NO_AUTH", message="请先登录家长账号"), 401
            return redirect(url_for("parent.login"))
        return fn(*a, **kw)
    return wrapper


def child_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        if not session.get("child_id"):
            if "/api/" in request.path:
                return jsonify(ok=False, code="NO_AUTH", message="请先输入PIN"), 401
            return redirect(url_for("child.login"))
        return fn(*a, **kw)
    return wrapper
