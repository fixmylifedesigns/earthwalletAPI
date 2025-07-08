from flask import Blueprint, jsonify
from auth.firebase import firebase_required
from models import Wallet
from extensions import db

wallet_bp = Blueprint('wallet', __name__)

@wallet_bp.route('/wallet', methods=['GET'])
@firebase_required
def get_wallet(current_user):
    """Get current user's wallet balance"""
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    
    if not wallet:
        # Create wallet if it doesn't exist
        wallet = Wallet(user_id=current_user.id)
        db.session.add(wallet)
        db.session.commit()
    
    return jsonify(wallet.to_dict()), 200

@wallet_bp.route('/transactions', methods=['GET'])
@firebase_required
def get_transactions(current_user):
    """Get user's transaction history"""
    from flask import request
    from models import Transaction
    
    limit = min(int(request.args.get('limit', 50)), 100)
    
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
        .order_by(Transaction.created_at.desc())\
        .limit(limit)\
        .all()
    
    return jsonify({
        'transactions': [t.to_dict() for t in transactions],
        'count': len(transactions)
    }), 200

@wallet_bp.route('/withdrawals', methods=['GET'])
@firebase_required
def get_withdrawals(current_user):
    """Get user's withdrawal history"""
    from flask import request
    from models import Withdrawal
    
    limit = min(int(request.args.get('limit', 20)), 50)
    
    withdrawals = Withdrawal.query.filter_by(user_id=current_user.id)\
        .order_by(Withdrawal.created_at.desc())\
        .limit(limit)\
        .all()
    
    return jsonify({
        'withdrawals': [w.to_dict() for w in withdrawals],
        'count': len(withdrawals)
    }), 200