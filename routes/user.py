# routes/user.py
from flask import Blueprint, jsonify
from auth.firebase import firebase_required

user_bp = Blueprint("user", __name__)

@user_bp.route("/user/kiosk-id")
@firebase_required
def my_kiosk_id(current_user):
    return jsonify(kiosk_id=current_user.kiosk_id or "")
