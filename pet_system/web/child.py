"""孩子端路由 /child 与孩子用写接口。"""
import uuid
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from ..services import award as award_svc, exchange as ex_svc, feeding as feed_svc
from ..db import fetch_all
from .auth import child_required, hash_pwd

import os
_tpl = os.path.join(os.path.dirname(__file__), "templates")
bp = Blueprint("child", __name__, url_prefix="/child", template_folder=_tpl)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json(silent=True) or request.form
        pin = str(data.get("pin", "")).strip()
        children = fetch_all("SELECT id, name, avatar, pin_hash, salt FROM child ORDER BY id")
        for ch in children:
            # PIN 允许未设置时 1234 兜底；已设置则校验 hash
            if ch["pin_hash"] and hash_pwd(pin, ch["salt"]) == ch["pin_hash"]:
                session["child_id"] = ch["id"]
                session["child_name"] = ch["name"]
                return jsonify(ok=True)
        return jsonify(ok=False, message="PIN 不对哦，再试一次"), 401
    return render_template("child_login.html")


@bp.route("/logout")
def logout():
    session.pop("child_id", None)
    return redirect(url_for("child.login"))


@bp.route("/")
@child_required
def home():
    return render_template("child_pet.html", name=session.get("child_name", "宝贝"))


@bp.route("/awards")
@child_required
def awards_page():
    return render_template("child_awards.html", name=session.get("child_name", "宝贝"))


@bp.route("/shop")
@child_required
def shop_page():
    return render_template("child_shop.html", name=session.get("child_name", "宝贝"))


@bp.route("/codex")
@child_required
def codex_page():
    return render_template("child_codex.html", name=session.get("child_name", "宝贝"))


# ---------- 孩子端 API ----------
@bp.route("/api/state")
@child_required
def api_state():
    return jsonify(ok=True, data=feed_svc.pet_view(session["child_id"]))


@bp.route("/api/say")
@child_required
def api_say():
    kind = request.args.get("kind", "line")
    avoid = request.args.get("avoid") or None
    r = feed_svc.say(session["child_id"], kind, avoid)
    return jsonify(ok=r.ok, message=r.message, code=r.code, data=r.value)


@bp.route("/api/awards")
@child_required
def api_awards():
    return jsonify(ok=True, data=award_svc.list_awards(session["child_id"]))


@bp.route("/api/claim", methods=["POST"])
@child_required
def api_claim():
    d = request.get_json() or {}
    r = award_svc.request_claim(session["child_id"], int(d.get("award_id", 0)))
    return jsonify(ok=r.ok, message=r.message, code=r.code)


@bp.route("/api/shop")
@child_required
def api_shop():
    return jsonify(ok=True, data=ex_svc.shop_view(session["child_id"]))


@bp.route("/api/exchange", methods=["POST"])
@child_required
def api_exchange():
    d = request.get_json() or {}
    r = ex_svc.exchange(session["child_id"], int(d.get("milk", 0)),
                        int(d.get("cookie", 0)), d.get("request_id") or str(uuid.uuid4()))
    return jsonify(ok=r.ok, message=r.message, code=r.code, data=r.value)


@bp.route("/api/feed", methods=["POST"])
@child_required
def api_feed():
    d = request.get_json() or {}
    r = feed_svc.feed(session["child_id"], d.get("request_id") or str(uuid.uuid4()))
    return jsonify(ok=r.ok, message=r.message, code=r.code, data=r.value)


@bp.route("/api/codex")
@child_required
def api_codex():
    return jsonify(ok=True, data=feed_svc.codex(session["child_id"]))
