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
        
        # If we have a subscription ID, try to get the current period end from Stripe
        # This applies to both active and canceled subscriptions
        if user.stripe_subscription_id:
            try:
                stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
                stripe_sub = stripe.Subscription.retrieve(user.stripe_subscription_id)
                
                from datetime import datetime
                # Access current_period_end from subscription items (correct location in Stripe API)
                period_end_timestamp = None
                if hasattr(stripe_sub, 'items') and hasattr(stripe_sub.items, 'data') and stripe_sub.items.data:
                    first_item = stripe_sub.items.data[0]
                    if hasattr(first_item, 'current_period_end') and first_item.current_period_end:
                        period_end_timestamp = first_item.current_period_end
                elif hasattr(stripe_sub, 'to_dict'):
                    # Fallback: use dictionary access to get items
                    sub_dict = stripe_sub.to_dict()
                    items = sub_dict.get('items', {})
                    items_data = items.get('data', [])
                    if items_data and len(items_data) > 0:
                        first_item = items_data[0]
                        period_end_timestamp = first_item.get('current_period_end')
                
                if period_end_timestamp:
                    current_period_end = datetime.fromtimestamp(period_end_timestamp)
                else:
                    logging.error(f"Could not access current_period_end from subscription items for subscription {user.stripe_subscription_id}")
                    return jsonify({'error': 'Unable to access subscription data'}), 500
                
                # Update the subscription status based on Stripe data
                # If cancel_at_period_end is True, the subscription is set to cancel
                if hasattr(stripe_sub, 'cancel_at_period_end') and stripe_sub.cancel_at_period_end:
                    user.subscription_status = 'canceled'
                    logging.info(f"Updated subscription status to 'canceled' for user {user.id} based on cancel_at_period_end flag")
                else:
                    user.subscription_status = stripe_sub.status
                
                # For active subscriptions, always update the end date
                # For canceled subscriptions, only update if it's not already set
                if user.subscription_status == 'active' or not user.subscription_end_date:
                    user.subscription_end_date = current_period_end
                    logging.info(f"Updated subscription end date for user {user.id} to {current_period_end}")
                
                db.session.commit()
                
            except Exception as e:
                logging.error(f"Error retrieving subscription from Stripe: {str(e)}")
        
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
        stripe_sub = stripe.Subscription.modify(
            user.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        # Update user's subscription status in the database
        user.subscription_status = 'canceled'
        
        # Set the subscription end date to the current period end from Stripe
        from datetime import datetime
        # Access current_period_end from subscription items (correct location in Stripe API)
        period_end_timestamp = None
        if hasattr(stripe_sub, 'items') and hasattr(stripe_sub.items, 'data') and stripe_sub.items.data:
            first_item = stripe_sub.items.data[0]
            if hasattr(first_item, 'current_period_end') and first_item.current_period_end:
                period_end_timestamp = first_item.current_period_end
        elif hasattr(stripe_sub, 'to_dict'):
            # Fallback: use dictionary access to get items
            sub_dict = stripe_sub.to_dict()
            items = sub_dict.get('items', {})
            items_data = items.get('data', [])
            if items_data and len(items_data) > 0:
                first_item = items_data[0]
                period_end_timestamp = first_item.get('current_period_end')
        
        if period_end_timestamp:
            current_period_end = datetime.fromtimestamp(period_end_timestamp)
        else:
            return jsonify({'error': 'Unable to access subscription end date'}), 500
        user.subscription_end_date = current_period_end
        
        db.session.commit()
        
        return jsonify({
            'message': 'Subscription will be canceled at the end of the billing period',
            'current_period_end': stripe_sub.current_period_end
        }), 200
        
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
        stripe_sub = stripe.Subscription.modify(
            user.stripe_subscription_id,
            cancel_at_period_end=False
        )
        
        # Update user's subscription status in the database
        user.subscription_status = 'active'
        user.is_premium = True
        db.session.commit()
        
        logging.info(f"Subscription reactivated for user {user.id} - cancel_at_period_end set to False")
        
        return jsonify({
            'message': 'Subscription reactivated successfully',
            'status': 'active'
        }), 200
        
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