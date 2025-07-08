# routes/withdraw.py
from flask import Blueprint, request, jsonify, current_app
from auth.firebase import firebase_required
from models import Wallet, Withdrawal
from extensions import db
import stripe, os
from datetime import datetime

withdraw_bp = Blueprint("withdraw", __name__)
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@withdraw_bp.route("/withdraw", methods=["POST"])
@firebase_required
def create_withdrawal(current_user):
    data = request.get_json(silent=True) or {}
    amount_cents = data.get("amount_cents")
    bank_token   = data.get("bank_token")

    # validation (unchanged) ...
    if not isinstance(amount_cents, int) or amount_cents <= 0:
        return jsonify(error="Amount must be a positive integer in cents"), 400
    if amount_cents < 100:
        return jsonify(error="Minimum withdrawal is $1.00"), 400
    if not bank_token or not isinstance(bank_token, str):
        return jsonify(error="Bank token required"), 400

    wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    if not wallet:
        return jsonify(error="Wallet not found"), 404
    if wallet.balance_cents < amount_cents:
        return jsonify(error="Insufficient balance"), 400

    withdrawal = Withdrawal(
        user_id=current_user.id,
        wallet_id=wallet.id,
        amount_cents=amount_cents,
        bank_token=bank_token,
        status="pending",
    )
    db.session.add(withdrawal)
    wallet.balance_cents -= amount_cents
    db.session.commit()            # withdrawal.id now exists

    # ───────────────── Stripe Payout ─────────────────
    try:
        if stripe.api_key and stripe.api_key.startswith("sk_"):
            payout = stripe.Payout.create(
                amount      = amount_cents,
                currency    = "usd",
                method      = "standard",          # or "instant"
                statement_descriptor = "RECYCLETEK",
                idempotency_key      = f"wd-{withdrawal.id}",
            )

            withdrawal.status = "completed"
            
            # Only set these fields if they exist in your model
            if hasattr(withdrawal, 'processed_at'):
                withdrawal.processed_at = datetime.utcnow()
            if hasattr(withdrawal, 'stripe_reference_id'):
                withdrawal.stripe_reference_id = payout.id
            
            db.session.commit()

        else:  # stub mode
            withdrawal.status = "completed"
            
            if hasattr(withdrawal, 'processed_at'):
                withdrawal.processed_at = datetime.utcnow()
            if hasattr(withdrawal, 'stripe_reference_id'):
                withdrawal.stripe_reference_id = f"stub_payout_{withdrawal.id}"
            
            db.session.commit()

    except stripe.error.StripeError as se:
        wallet.balance_cents += amount_cents   # undo debit
        withdrawal.status = "failed"
        db.session.commit()
        current_app.logger.error(f"Stripe payout error: {se}")
        return jsonify(error="Payout failed"), 500
    except Exception as e:
        # Catch any other errors (like database/attribute errors)
        wallet.balance_cents += amount_cents   # undo debit
        withdrawal.status = "failed"
        db.session.commit()
        current_app.logger.error(f"Withdrawal processing error: {e}")
        return jsonify(error="Withdrawal processing failed"), 500

    # Safe response construction
    try:
        response_data = {
            "success": True,
            "withdrawal": {
                "id": withdrawal.id,
                "user_id": withdrawal.user_id,
                "amount_cents": withdrawal.amount_cents,
                "status": withdrawal.status,
                "created_at": withdrawal.created_at.isoformat() if hasattr(withdrawal, 'created_at') else None,
            },
            "new_balance_cents": wallet.balance_cents,
            "new_balance_dollars": wallet.balance_cents / 100,
        }
        
        # Add optional fields if they exist
        if hasattr(withdrawal, 'processed_at') and withdrawal.processed_at:
            response_data["withdrawal"]["processed_at"] = withdrawal.processed_at.isoformat()
        if hasattr(withdrawal, 'stripe_reference_id') and withdrawal.stripe_reference_id:
            response_data["withdrawal"]["stripe_reference_id"] = withdrawal.stripe_reference_id
        
        return jsonify(response_data), 201
        
    except Exception as e:
        current_app.logger.error(f"Response construction error: {e}")
        return jsonify(error="Response construction failed"), 500