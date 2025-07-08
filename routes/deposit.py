from flask import Blueprint, request, jsonify, g
from auth.firebase import firebase_required, kiosk_only
from models import User, Wallet, Transaction
from extensions import db, limiter

deposit_bp = Blueprint("deposit", __name__)

MATERIAL_RATES = {"plastic": 5, "aluminum": 10}

@deposit_bp.route("/deposit", methods=["POST"])
@firebase_required
@limiter.limit("5 per second", key_func=lambda: f"deposit:{g.current_user.id}")
def create_deposit(current_user):
    """Create a deposit transaction - supports Firebase auth, test bypass, and kiosk ID"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    
    material = data.get('material')
    units = data.get('units')
    
    # Validation
    if not material or material not in MATERIAL_RATES:
        return jsonify({'error': 'Invalid material. Must be "plastic" or "aluminum"'}), 400
    
    if not isinstance(units, int) or units <= 0:
        return jsonify({'error': 'Units must be a positive integer'}), 400
    
    if units > 1000:
        return jsonify({'error': 'Maximum 1000 units per deposit'}), 400
    
    # Calculate amount
    amount_cents = units * MATERIAL_RATES[material]
    
    # Get or create wallet
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id)
        db.session.add(wallet)
        db.session.flush()  # Get the wallet ID
    
    # Create transaction
    transaction = Transaction(
        user_id=current_user.id,
        wallet_id=wallet.id,
        transaction_type='deposit',
        material=material,
        units=units,
        amount_cents=amount_cents
    )
    db.session.add(transaction)
    
    # Update wallet balance
    wallet.balance_cents += amount_cents
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'transaction': transaction.to_dict(),
            'new_balance_cents': wallet.balance_cents,
            'new_balance_dollars': wallet.balance_cents / 100,
            'user_info': {
                'email': current_user.email,
                'kiosk_id': current_user.kiosk_id
            }
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

@deposit_bp.route("/deposit/kiosk", methods=["POST"])
@kiosk_only
@limiter.limit("10 per second", key_func=lambda: f"kiosk_deposit:{g.current_user.id}")
def create_kiosk_deposit(current_user):
    """Create a deposit transaction - kiosk-only endpoint that only accepts kiosk ID"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    
    material = data.get('material')
    units = data.get('units')
    
    # Validation
    if not material or material not in MATERIAL_RATES:
        return jsonify({'error': 'Invalid material. Must be "plastic" or "aluminum"'}), 400
    
    if not isinstance(units, int) or units <= 0:
        return jsonify({'error': 'Units must be a positive integer'}), 400
    
    if units > 1000:
        return jsonify({'error': 'Maximum 1000 units per deposit'}), 400
    
    # Calculate amount
    amount_cents = units * MATERIAL_RATES[material]
    
    # Get or create wallet
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id)
        db.session.add(wallet)
        db.session.flush()
    
    # Create transaction with kiosk flag
    transaction = Transaction(
        user_id=current_user.id,
        wallet_id=wallet.id,
        transaction_type='deposit',
        material=material,
        units=units,
        amount_cents=amount_cents
    )
    db.session.add(transaction)
    
    # Update wallet balance
    wallet.balance_cents += amount_cents
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Deposit successful! ${amount_cents/100:.2f} added to account.',
            'transaction': transaction.to_dict(),
            'new_balance_cents': wallet.balance_cents,
            'new_balance_dollars': wallet.balance_cents / 100,
            'user_email': current_user.email
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error occurred'}), 500

@deposit_bp.route("/user/kiosk-id", methods=["GET"])
@firebase_required
def get_user_kiosk_id(current_user):
    """Get the current user's kiosk ID"""
    return jsonify({
        'kiosk_id': current_user.kiosk_id,
        'email': current_user.email,
        'user_id': current_user.id
    }), 200
    
@deposit_bp.route("/validate-kiosk-id", methods=["POST"])
def validate_kiosk_id():
    """Validate if a kiosk ID exists - public endpoint for kiosk validation"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    
    kiosk_id = data.get('kiosk_id')
    
    if not kiosk_id:
        return jsonify({'error': 'kiosk_id is required'}), 400
    
    if len(kiosk_id) != 8:
        return jsonify({'error': 'kiosk_id must be 8 characters'}), 400
    
    # Check if user exists with this kiosk ID
    user = User.query.filter_by(kiosk_id=kiosk_id.upper()).first()
    
    if not user:
        return jsonify({'error': 'Invalid kiosk ID'}), 404
    
    return jsonify({
        'valid': True,
        'user_email': user.email,
        'message': f'Kiosk ID validated for {user.email}'
    }), 200
    """Validate if a kiosk ID exists - public endpoint for kiosk validation"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'JSON body required'}), 400
    
    kiosk_id = data.get('kiosk_id')
    
    if not kiosk_id:
        return jsonify({'error': 'kiosk_id is required'}), 400
    
    if len(kiosk_id) != 8:
        return jsonify({'error': 'kiosk_id must be 8 characters'}), 400
    
    # Check if user exists with this kiosk ID
    user = User.query.filter_by(kiosk_id=kiosk_id.upper()).first()
    
    if not user:
        return jsonify({'error': 'Invalid kiosk ID'}), 404
    
    return jsonify({
        'valid': True,
        'user_email': user.email,
        'message': f'Kiosk ID validated for {user.email}'
    }), 200