from flask import Blueprint, request, jsonify, current_app, g
from flask_cors import cross_origin
import stripe
import os
from app import db
from app.models.user import User
from app.middleware.auth import require_auth
from app.middleware.subscription import premium_required
import logging

subscription_bp = Blueprint('subscription', __name__)

@subscription_bp.route('/status', methods=['GET'])
@cross_origin(supports_credentials=True)
@require_auth
def get_subscription_status():
    """Get user's current subscription status"""
    try:
        user = User.query.get(g.user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        status = {
            'is_premium': user.is_premium,
            'subscription_status': user.subscription_status,
            'stripe_customer_id': user.stripe_customer_id,
            'stripe_subscription_id': user.stripe_subscription_id,
            'subscription_start_date': user.subscription_start_date.isoformat() if user.subscription_start_date else None,
            'subscription_end_date': user.subscription_end_date.isoformat() if user.subscription_end_date else None,
            'last_payment_date': user.last_payment_date.isoformat() if user.last_payment_date else None,
            'payment_failed': user.payment_failed
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logging.error(f"Error getting subscription status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@subscription_bp.route('/cancel', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
@premium_required
def cancel_subscription():
    """Cancel user's subscription"""
    try:
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        user = User.query.get(g.user_id)
        if not user or not user.stripe_subscription_id:
            return jsonify({'error': 'No active subscription found'}), 404
        
        # Cancel subscription in Stripe
        stripe.Subscription.modify(
            user.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        return jsonify({'message': 'Subscription will be canceled at the end of the billing period'}), 200
        
    except Exception as e:
        logging.error(f"Error canceling subscription: {str(e)}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500

@subscription_bp.route('/reactivate', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
def reactivate_subscription():
    """Reactivate a canceled subscription"""
    try:
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        user = User.query.get(g.user_id)
        if not user or not user.stripe_subscription_id:
            return jsonify({'error': 'No subscription found'}), 404
        
        # Reactivate subscription in Stripe
        stripe.Subscription.modify(
            user.stripe_subscription_id,
            cancel_at_period_end=False
        )
        
        return jsonify({'message': 'Subscription reactivated successfully'}), 200
        
    except Exception as e:
        logging.error(f"Error reactivating subscription: {str(e)}")
        return jsonify({'error': 'Failed to reactivate subscription'}), 500

@subscription_bp.route('/billing-portal', methods=['POST'])
@cross_origin(supports_credentials=True)
@require_auth
@premium_required
def create_billing_portal_session():
    """Create a Stripe billing portal session"""
    try:
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        user = User.query.get(g.user_id)
        if not user or not user.stripe_customer_id:
            return jsonify({'error': 'No customer found'}), 404
        
        # Create billing portal session
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=os.getenv('FRONTEND_URL') + '/subscription'
        )
        
        return jsonify({'url': session.url}), 200
        
    except Exception as e:
        logging.error(f"Error creating billing portal session: {str(e)}")
        return jsonify({'error': 'Failed to create billing portal session'}), 500 