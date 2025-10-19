from flask import Blueprint, request, jsonify, g, make_response
from flask_cors import cross_origin
from app.middleware.auth import require_auth
from app.services.credit_system_service import CreditSystemService
import logging
from app.models.user import User
from app import db
from datetime import datetime

credit_system_bp = Blueprint('credit_system', __name__)
logger = logging.getLogger(__name__)

def add_cors_headers(response):
    """Add CORS headers to response"""
    origin = request.headers.get('Origin')
    allowed_origins = ['http://localhost:3000', 'http://localhost:3005']
    
    if origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
    else:
        response.headers['Access-Control-Allow-Origin'] = 'http://localhost:3000'
    
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Accept, Origin'
    response.headers['Vary'] = 'Origin'
    return response

@credit_system_bp.route('/status', methods=['OPTIONS'])
@credit_system_bp.route('/claim-daily', methods=['OPTIONS'])
@credit_system_bp.route('/estimate-cost', methods=['OPTIONS'])
@credit_system_bp.route('/purchase', methods=['OPTIONS'])
@credit_system_bp.route('/process-purchase', methods=['OPTIONS'])
@credit_system_bp.route('/monthly-refill', methods=['OPTIONS'])
@credit_system_bp.route('/check-action', methods=['OPTIONS'])
@credit_system_bp.route('/packages', methods=['OPTIONS'])
def handle_preflight():
    """Handle CORS preflight requests"""
    response = make_response()
    return add_cors_headers(response)

@credit_system_bp.route('/status', methods=['GET'])
@require_auth
def get_credit_status():
    """Get user's current credit status and plan information"""
    try:
        credit_service = CreditSystemService()
        status = credit_service.get_user_credit_status(g.user_id)
        
        if not status:
            response = make_response(jsonify({'error': 'Failed to retrieve credit status'}), 500)
            return add_cors_headers(response)
        
        response = make_response(jsonify({
            'success': True,
            'data': status
        }), 200)
        return add_cors_headers(response)
        
    except Exception as e:
        logger.error(f"Error getting credit status: {str(e)}")
        response = make_response(jsonify({'error': 'Internal server error'}), 500)
        return add_cors_headers(response)

@credit_system_bp.route('/claim-daily', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def claim_daily_credits():
    """Claim daily free credits (only for free users)"""
    try:
        credit_service = CreditSystemService()
        success, message, credits_claimed = credit_service.claim_daily_credits(g.user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'credits_claimed': credits_claimed
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error claiming daily credits: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@credit_system_bp.route('/estimate-cost', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def estimate_action_cost():
    """Estimate cost for an action before performing it"""
    try:
        data = request.get_json()
        action = data.get('action')
        metadata = data.get('metadata', {})
        
        if not action:
            return jsonify({'error': 'Action is required'}), 400
        
        credit_service = CreditSystemService()
        estimate = credit_service.estimate_action_cost(action, metadata)
        
        return jsonify({
            'success': True,
            'data': estimate
        }), 200
        
    except Exception as e:
        logger.error(f"Error estimating cost: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@credit_system_bp.route('/purchase', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def initiate_credit_purchase():
    """Initiate credit purchase (only for Elite users)"""
    try:
        data = request.get_json()
        package_id = data.get('package_id')
        
        if not package_id:
            return jsonify({'error': 'Package ID is required'}), 400
        
        # Check if user is Elite
        user = User.query.get(g.user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not (user.is_premium and user.subscription_status == 'active'):
            return jsonify({
                'error': 'Elite subscription required',
                'message': 'Only Elite users can purchase additional credits'
            }), 403
        
        credit_service = CreditSystemService()
        packages = credit_service.CREDIT_PACKAGES
        
        if package_id not in packages:
            return jsonify({'error': 'Invalid package ID'}), 400
        
        package = packages[package_id]
        total_credits = package['credits'] + package['bonus']
        
        # This would integrate with your existing Stripe payment processing
        # For now, return the payment information
        return jsonify({
            'success': True,
            'payment_info': {
                'package_id': package_id,
                'credits': total_credits,
                'price': package['price'],
                'description': f"{total_credits} credits (${total_credits/100:.2f} value)"
            },
            'redirect_url': f'/payment?package={package_id}&amount={package["price"]}&credits={total_credits}'
        }), 200
        
    except Exception as e:
        logger.error(f"Error initiating credit purchase: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@credit_system_bp.route('/process-purchase', methods=['POST'])
@require_auth
def process_credit_purchase():
    """Process successful credit purchase (called after Stripe payment)"""
    try:
        data = request.get_json()
        package_id = data.get('package_id')
        payment_intent_id = data.get('payment_intent_id')
        
        if not package_id or not payment_intent_id:
            return jsonify({'error': 'Package ID and payment intent ID are required'}), 400
        
        # Verify payment with Stripe (you would implement this)
        # For now, assume payment is verified
        
        credit_service = CreditSystemService()
        packages = credit_service.CREDIT_PACKAGES
        
        if package_id not in packages:
            return jsonify({'error': 'Invalid package ID'}), 400
        
        package = packages[package_id]
        total_credits = package['credits'] + package['bonus']
        
        # Add credits to user account
        success = credit_service.add_credits(
            g.user_id, 
            total_credits, 
            'purchase', 
            {
                'package_id': package_id,
                'payment_intent_id': payment_intent_id,
                'price': package['price']
            }
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Successfully added {total_credits} credits to your account',
                'credits_added': total_credits
            }), 200
        else:
            return jsonify({'error': 'Failed to add credits'}), 500
            
    except Exception as e:
        logger.error(f"Error processing credit purchase: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@credit_system_bp.route('/monthly-refill', methods=['POST'])
@require_auth
def manual_monthly_refill():
    """Manual monthly refill for Elite users (admin/testing purposes)"""
    try:
        credit_service = CreditSystemService()
        success, message, credits_added = credit_service.refill_monthly_credits(g.user_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'credits_added': credits_added
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400
            
    except Exception as e:
        logger.error(f"Error with monthly refill: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@credit_system_bp.route('/costs', methods=['GET'])
def get_credit_costs():
    """Get current credit costs for all actions (public endpoint)"""
    try:
        credit_service = CreditSystemService()
        
        return jsonify({
            'success': True,
            'data': {
                'credit_costs': credit_service.CREDIT_COSTS,
                'subscription_plans': credit_service.SUBSCRIPTION_PLANS,
                'credit_packages': credit_service.CREDIT_PACKAGES
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting credit costs: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@credit_system_bp.route('/check-action', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def check_action_credits():
    """Check if user has enough credits for an action"""
    try:
        data = request.get_json()
        action = data.get('action')
        metadata = data.get('metadata', {})
        
        if not action:
            return jsonify({'error': 'Action is required'}), 400
        
        credit_service = CreditSystemService()
        can_perform, message, cost = credit_service.check_and_deduct_credits(
            g.user_id, action, metadata
        )
        
        return jsonify({
            'success': can_perform,
            'message': message,
            'cost': cost,
            'can_perform': can_perform
        }), 200
        
    except Exception as e:
        logging.error(f"Error checking action credits: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@credit_system_bp.route('/packages', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_credit_packages():
    """Get available credit packages"""
    try:
        credit_service = CreditSystemService()
        
        return jsonify({
            'success': True,
            'packages': credit_service.CREDIT_PACKAGES,
            'subscription_tiers': credit_service.SUBSCRIPTION_TIERS
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting credit packages: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500 