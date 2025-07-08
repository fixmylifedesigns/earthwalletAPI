# auth/firebase.py
from functools import wraps
from flask import request, jsonify, current_app, g
import firebase_admin
from firebase_admin import credentials, auth
from models import User
from extensions import db
import json, os, secrets, string

# ───────────────────────── Firebase bootstrap ─────────────────────────
try:
    firebase_admin.get_app()
except ValueError:                       # first run
    service_account_info = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT"])
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)

# ────────────────────────── helpers ───────────────────────────────────
def generate_kiosk_id() -> str:
    """Generate a unique 8-character alphanumeric kiosk ID."""
    while True:
        kiosk_id = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
        if not User.query.filter_by(kiosk_id=kiosk_id).first():
            return kiosk_id

# ────────────────────────── main decorator ────────────────────────────
def firebase_required(view):
    """Accept   ① dev bypass   ② kiosk-ID   ③ Firebase Bearer token."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        current_app.logger.info("=== Auth Debug ===")
        current_app.logger.info(f"{request.method} {request.url}")
        current_app.logger.info(f"Headers: {dict(request.headers)}")

        # ---------- 1) dev bypass ------------------------------------------------
        test_hdr   = request.headers.get("X-Test-User-Email")
        test_email = os.getenv("TEST_USER_EMAIL")
        if test_hdr and test_email and test_hdr == test_email:
            user = User.query.filter_by(email=test_hdr).first()
            if not user:
                user = User(
                    firebase_uid=f"test-{test_hdr}",
                    email=test_hdr,
                    kiosk_id=generate_kiosk_id(),
                )
                db.session.add(user)
                db.session.commit()
            else:
                if not user.kiosk_id:
                    user.kiosk_id = generate_kiosk_id()
                    db.session.commit()
            g.current_user = user
            return view(user, *args, **kwargs)

        # ---------- 2) kiosk-ID --------------------------------------------------
        raw_json = request.get_json(silent=True)  # never raises
        kiosk_id = request.headers.get("X-Kiosk-User-ID") or (raw_json or {}).get("kiosk_id")
        if kiosk_id:
            user = User.query.filter_by(kiosk_id=kiosk_id.upper()).first()
            if not user:
                return jsonify(error="Invalid kiosk ID"), 401
            g.current_user = user
            return view(user, *args, **kwargs)

        # ---------- 3) Firebase Bearer token ------------------------------------
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify(
                error="Authorization required. Use Bearer token, "
                      "X-Kiosk-User-ID header, or kiosk_id in body"
            ), 401

        id_token = auth_header.split(" ", 1)[1]
        try:
            decoded = auth.verify_id_token(id_token)
        except Exception as e:  # noqa: BLE001
            current_app.logger.warning(f"Token verify failed: {e}")
            return jsonify(error="Invalid or expired token"), 401

        uid   = decoded["uid"]
        email = decoded.get("email")
        if not email:
            return jsonify(error="Email claim missing"), 401

        user = User.query.filter_by(firebase_uid=uid).first()
        if not user:
            user = User(firebase_uid=uid, email=email, kiosk_id=generate_kiosk_id())
            db.session.add(user)
            db.session.commit()
        else:
            if not user.kiosk_id:
                user.kiosk_id = generate_kiosk_id()
                db.session.commit()

        g.current_user = user
        return view(user, *args, **kwargs)

    return wrapped

# ───────────────────── kiosk-only decorator ───────────────────────────
def kiosk_only(view):
    """Endpoint accessible **only** with a kiosk ID."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        raw_json = request.get_json(silent=True)
        kiosk_id = request.headers.get("X-Kiosk-User-ID") or (raw_json or {}).get("kiosk_id")
        if not kiosk_id:
            return jsonify(error="Kiosk ID required"), 401

        user = User.query.filter_by(kiosk_id=kiosk_id.upper()).first()
        if not user:
            return jsonify(error="Invalid kiosk ID"), 401

        g.current_user = user
        return view(user, *args, **kwargs)

    return wrapped
