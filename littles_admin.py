"""
littles_admin.py — Siss Littles Admin Routes

Add these routes to littles_web.py by calling register_admin_routes(app)
at the bottom of create_app(), or paste directly into littles_web.py.

Admin endpoints:
  POST /littles/api/admin/remove_user   → Remove a family member by username
  POST /littles/api/admin/restore_user  → Restore a removed user
  GET  /littles/api/admin/users         → List all users (paginated)

Protected by ADMIN_KEY environment variable (same key works across both apps).

Founded by T.L. Powers · Siss Littles · 2026
"""

import os
from datetime import datetime, timezone
from flask import jsonify, request
from littles_database import get_session, FamilyMember

ADMIN_KEY = os.environ.get("ADMIN_KEY", "")


def check_admin(req) -> bool:
    if not ADMIN_KEY:
        return False
    auth = req.headers.get("Authorization", "")
    xkey = req.headers.get("X-Admin-Key", "")
    token = auth.replace("Bearer ", "").strip() if auth.startswith("Bearer ") else xkey.strip()
    return token == ADMIN_KEY


def register_admin_routes(app):
    """Call this in littles_web.py inside create_app(): register_admin_routes(app)"""

    @app.route("/littles/api/admin/remove_user", methods=["POST"])
    def littles_admin_remove_user():
        if not check_admin(request):
            return jsonify({"ok": False, "error": "Unauthorized."}), 401

        data     = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip().lower()
        reason   = (data.get("reason") or "No reason provided.").strip()[:500]

        if not username:
            return jsonify({"ok": False, "error": "username required."}), 400

        session = get_session()
        try:
            member = session.query(FamilyMember).filter(
                FamilyMember.username == username
            ).first()

            if not member:
                return jsonify({"ok": False, "error": "User not found."}), 404

            member.is_suspended  = True
            member.is_active     = False
            session.commit()

            return jsonify({
                "ok":       True,
                "username": username,
                "removed":  True,
                "reason":   reason,
            })

        except Exception as e:
            session.rollback()
            print(f"[Littles Admin] remove_user error: {e}")
            return jsonify({"ok": False, "error": "Failed to remove user."}), 500
        finally:
            session.close()

    @app.route("/littles/api/admin/restore_user", methods=["POST"])
    def littles_admin_restore_user():
        if not check_admin(request):
            return jsonify({"ok": False, "error": "Unauthorized."}), 401

        data     = request.get_json(silent=True) or {}
        username = (data.get("username") or "").strip().lower()

        if not username:
            return jsonify({"ok": False, "error": "username required."}), 400

        session = get_session()
        try:
            member = session.query(FamilyMember).filter(
                FamilyMember.username == username
            ).first()

            if not member:
                return jsonify({"ok": False, "error": "User not found."}), 404

            member.is_suspended = False
            member.is_active    = True
            session.commit()

            return jsonify({"ok": True, "username": username, "restored": True})

        except Exception as e:
            session.rollback()
            return jsonify({"ok": False, "error": "Failed to restore user."}), 500
        finally:
            session.close()

    @app.route("/littles/api/admin/users", methods=["GET"])
    def littles_admin_list_users():
        if not check_admin(request):
            return jsonify({"ok": False, "error": "Unauthorized."}), 401

        page     = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 50))
        offset   = (page - 1) * per_page

        session = get_session()
        try:
            total   = session.query(FamilyMember).count()
            members = session.query(FamilyMember).order_by(
                FamilyMember.created_at.desc()
            ).offset(offset).limit(per_page).all()

            return jsonify({
                "ok":    True,
                "total": total,
                "page":  page,
                "users": [
                    {
                        "username":     m.username,
                        "display_name": m.display_name,
                        "role":         m.role,
                        "family_id":    m.family_id,
                        "is_active":    m.is_active,
                        "is_suspended": m.is_suspended,
                        "joined_at":    m.created_at.isoformat(),
                        "last_active":  m.last_active.isoformat() if m.last_active else None,
                    }
                    for m in members
                ],
            })

        except Exception as e:
            return jsonify({"ok": False, "error": "Failed to list users."}), 500
        finally:
            session.close()
