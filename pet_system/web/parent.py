"""家长端路由 /parent（账号登录 + 配置入库）。"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from ..services import award as award_svc, settings as set_svc, ledger as ledger_svc
from ..db import fetch_one
from .auth import parent_required, hash_pwd

import os
_tpl = os.path.join(os.path.dirname(__file__), "templates")
bp = Blueprint("parent", __name__, url_prefix="/parent", template_folder=_tpl)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        d = request.get_json(silent=True) or request.form
        u = fetch_one("SELECT id, username, password_hash, salt FROM admin_user WHERE username=%s",
                      (d.get("username"),))
        if u and hash_pwd(str(d.get("password", "")), u["salt"]) == u["password_hash"]:
            session["parent"] = u["username"]
            return jsonify(ok=True)
        return jsonify(ok=False, message="账号或密码不对"), 401
    return render_template("parent_login.html")


@bp.route("/logout")
def logout():
    session.pop("parent", None)
    return redirect(url_for("parent.login"))


@bp.route("/")
@parent_required
def dashboard():
    return render_template("parent_dashboard.html")


@bp.route("/pending")
@parent_required
def pending_page():
    return render_template("parent_pending.html")


@bp.route("/awards")
@parent_required
def awards_page():
    return render_template("parent_awards.html")


@bp.route("/settings")
@parent_required
def settings_page():
    return render_template("parent_settings.html")


# ---------- 家长 API ----------
@bp.route("/api/pending")
@parent_required
def api_pending():
    rows = award_svc.pending_claims()
    return jsonify(ok=True, data=[dict(r) for r in rows])


@bp.route("/api/decide", methods=["POST"])
@parent_required
def api_decide():
    d = request.get_json() or {}
    r = award_svc.decide_claim(int(d.get("claim_id", 0)), bool(d.get("approve")),
                               None, d.get("note"))
    return jsonify(ok=r.ok, message=r.message, code=r.code)


@bp.route("/api/config")
@parent_required
def api_config():
    return jsonify(ok=True, data=set_svc.get_all())


@bp.route("/api/config", methods=["POST"])
@parent_required
def api_config_update():
    d = request.get_json() or {}
    set_svc.update(d.get("key"), d.get("value"), session.get("parent", "admin"))
    return jsonify(ok=True, message="配置已保存")


@bp.route("/api/awards")
@parent_required
def api_awards():
    return jsonify(ok=True, data=[dict(r) for r in set_svc.list_awards_admin()])


@bp.route("/api/award/update", methods=["POST"])
@parent_required
def api_award_update():
    d = request.get_json() or {}
    set_svc.update_award(int(d.pop("id", 0)), d, session.get("parent", "admin"))
    return jsonify(ok=True, message="奖项已保存")


@bp.route("/api/verify")
@parent_required
def api_verify():
    return jsonify(ok=True, data=ledger_svc.verify(1))


@bp.route("/api/children")
@parent_required
def api_children():
    from ..db import fetch_all
    return jsonify(ok=True, data=fetch_all("SELECT id,name,avatar,points_balance FROM child ORDER BY id"))
