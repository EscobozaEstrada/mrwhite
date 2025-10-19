from flask import Blueprint, request, jsonify, current_app, make_response
from flask_cors import CORS, cross_origin
import stripe
import json
import os
from app import db
from app.models.user import User
from app.services.credit_system_service import CreditSystemService
import logging

payment_bp = Blueprint('payment', __name__)

@payment_bp.route('/create-payment-intent', methods=['POST'])
def create_payment():
    try:
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        data = request.json
        logging.info(f"Creating payment intent with data: {data}")
        
        # Check if this is a credit purchase
        package_id = data.get('package_id')
        user_id = data.get('user_id')
        is_credit_purchase = package_id is not None
        
        logging.info(f"Payment intent request - Package ID: {package_id}, User ID: {user_id}, Is credit purchase: {is_credit_purchase}")
        
        # Create metadata for the payment intent
        metadata = {
            'type': 'credit_purchase' if is_credit_purchase else 'subscription',
        }
        
        if is_credit_purchase:
            metadata['package_id'] = package_id
            # Get user_id if available
            if user_id:
                metadata['user_id'] = str(user_id)
            
            logging.info(f"Credit purchase metadata: {metadata}")
        else:
            logging.info(f"Subscription payment metadata: {metadata}")
        
        intent = stripe.PaymentIntent.create(
            amount=data['amount'],
            currency='usd',
            payment_method_types=['card'],
            metadata=metadata
        )
        
        logging.info(f"Payment intent created successfully - ID: {intent.id}, Metadata: {intent.metadata}")
        
        return jsonify({'clientSecret': intent.client_secret})
    except Exception as e:
        logging.error(f"Error creating payment intent: {str(e)}")
        return jsonify({"Internal Server Error": str(e)}), 500

@payment_bp.route('/create-checkout-session', methods=['POST', 'OPTIONS'])
def create_checkout_session():
    # Get the origin from the request
    origin = request.headers.get('Origin', '')
    allowed_origins = [os.getenv('FRONTEND_URL', 'http://localhost:3000'), 'http://localhost:3000', 'http://localhost:3005']
    
    # Use the actual origin if it's in the allowed list, otherwise use the configured frontend URL
    if origin in allowed_origins:
        cors_origin = origin
    else:
        cors_origin = os.getenv('FRONTEND_URL', 'http://localhost:3000')
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', cors_origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 200
        
    try:
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        price_id = os.getenv('STRIPE_PRICE_ID')
        
        # Get user information if available
        user_email = request.json.get('email', None)
        user_id = request.json.get('user_id', None)
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price': price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=request.json.get('success_url', os.getenv('FRONTEND_URL', 'http://localhost:3000') + '/payment-success?amount=28.95&type=subscription'),
            cancel_url=request.json.get('cancel_url', os.getenv('FRONTEND_URL', 'http://localhost:3000') + '/subscription'),
            client_reference_id=user_id,  # Store user ID for webhook
            customer_email=user_email,    # Pre-fill customer email
            metadata={
                'user_id': user_id if user_id else 'anonymous'
            }
        )
        
        # Create a custom response with proper CORS headers
        response = make_response(jsonify({'url': checkout_session.url}))
        response.headers.add('Access-Control-Allow-Origin', cors_origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
        
    except Exception as e:
        # Also add CORS headers to error responses
        error_response = make_response(jsonify({"error": str(e)}))
        error_response.headers.add('Access-Control-Allow-Origin', cors_origin)
        error_response.headers.add('Access-Control-Allow-Credentials', 'true')
        return error_response, 500

@payment_bp.route('/verify-and-process-credit-purchase', methods=['POST'])
@cross_origin(supports_credentials=True)
def verify_and_process_credit_purchase():
    """Verify payment intent and process credit purchase manually"""
    try:
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        data = request.json
        payment_intent_id = data.get('payment_intent_id')
        user_id = data.get('user_id')
        
        logging.info(f"Processing credit purchase - Payment Intent: {payment_intent_id}, User: {user_id}")
        
        if not payment_intent_id or not user_id:
            return jsonify({'error': 'Payment intent ID and user ID are required'}), 400
        
        # Retrieve the payment intent from Stripe to verify it
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            logging.info(f"Payment intent retrieved - Status: {payment_intent.status}")
        except stripe.error.InvalidRequestError as e:
            logging.error(f"Invalid payment intent: {str(e)}")
            return jsonify({'error': 'Invalid payment intent ID'}), 400
        
        # Check if payment was successful
        if payment_intent.status != 'succeeded':
            logging.warning(f"Payment not completed - Status: {payment_intent.status}")
            return jsonify({'error': f'Payment not completed. Status: {payment_intent.status}'}), 400
        
        # Check if this is a credit purchase
        metadata = payment_intent.get('metadata', {})
        payment_type = metadata.get('type')
        package_id = metadata.get('package_id')
        
        # Allow package_id to be specified in request data if not in metadata
        # This provides flexibility for cases where payment intent wasn't created specifically for credit purchase
        request_package_id = data.get('package_id')
        if not package_id and request_package_id:
            package_id = request_package_id
            logging.info(f"Using package_id from request data: {package_id}")
        
        # Enhanced flexible check - if we have package_id, treat it as credit purchase
        # This handles cases where payment_type might be 'subscription' but it's actually a credit purchase
        if package_id:
            payment_type = 'credit_purchase'
            logging.info(f"Found package_id, treating as credit purchase: {package_id}")
        elif not payment_type:
            # Fallback for completely empty metadata
            logging.error("No payment type or package_id found in metadata or request")
            return jsonify({'error': 'Payment intent metadata is incomplete - no type or package_id found. Please specify package_id in request.'}), 400
        
        if payment_type != 'credit_purchase':
            logging.error(f"Not a credit purchase - Payment type: {payment_type}, Package ID: {package_id}")
            return jsonify({'error': f'Not a credit purchase. Payment type: {payment_type}. Specify package_id in request to process as credit purchase.'}), 400
        
        # package_id is already extracted above
        metadata_user_id = metadata.get('user_id')
        
        # If user_id not in metadata, it's okay - we'll use the one from request
        if not metadata_user_id:
            metadata_user_id = str(user_id)
            logging.info(f"Using user_id from request data: {metadata_user_id}")
        
        # Verify user ID matches (be flexible with string/int conversion)
        if str(user_id) != str(metadata_user_id):
            logging.error(f"User ID mismatch - Expected: {metadata_user_id}, Got: {user_id}")
            return jsonify({'error': f'User ID mismatch. Expected: {metadata_user_id}, Got: {user_id}'}), 400
        
        if not package_id:
            logging.error("Package ID not found in payment metadata")
            return jsonify({'error': 'Package ID not found in payment metadata'}), 400
        
        # Get user and verify they exist and are Elite
        user = User.query.get(user_id)
        if not user:
            logging.error(f"User not found: {user_id}")
            return jsonify({'error': 'User not found'}), 404
        
        # Log current user state
        logging.info(f"User {user_id} - Current balance: {user.credits_balance}, Premium: {user.is_premium}, Status: {user.subscription_status}")
        
        # Verify user is Elite (required for credit purchases)
        if not (user.is_premium and user.subscription_status == 'active'):
            logging.error(f"User {user_id} not Elite - Premium: {user.is_premium}, Status: {user.subscription_status}")
            return jsonify({'error': 'Elite subscription required for credit purchases'}), 403
        
        # Process the credit purchase
        credit_service = CreditSystemService()
        packages = credit_service.CREDIT_PACKAGES
        
        if package_id not in packages:
            logging.error(f"Invalid package ID: {package_id}. Available: {list(packages.keys())}")
            return jsonify({'error': f'Invalid package ID: {package_id}. Available: {list(packages.keys())}'}), 400
        
        package = packages[package_id]
        total_credits = package['credits'] + package['bonus']
        
        logging.info(f"Processing credit package {package_id}: {total_credits} credits (${package['price']/100:.2f})")
        
        # Store balance before credit addition
        balance_before = user.credits_balance
        
        # Add credits to user account
        success = credit_service.add_credits(
            user_id,
            total_credits,
            'purchase',
            {
                'package_id': package_id,
                'payment_intent_id': payment_intent_id,
                'price': package['price']
            }
        )
        
        if success:
            # Refresh user object to get updated balance
            db.session.refresh(user)
            balance_after = user.credits_balance
            
            logging.info(f"✅ Credits added successfully to user {user_id}: {balance_before} → {balance_after} (+{total_credits})")
            
            # Verify the balance actually increased
            if balance_after == balance_before + total_credits:
                logging.info(f"✅ Balance verification passed: {balance_after} = {balance_before} + {total_credits}")
            else:
                logging.warning(f"⚠️ Balance verification failed: Expected {balance_before + total_credits}, got {balance_after}")
            
            return jsonify({
                'success': True,
                'message': f'Successfully added {total_credits} credits to your account',
                'credits_added': total_credits,
                'balance_before': balance_before,
                'new_balance': balance_after,
                'package_details': package,
                'verification_passed': balance_after == balance_before + total_credits
            }), 200
        else:
            logging.error(f"❌ Failed to add credits for user {user_id}")
            return jsonify({'error': 'Failed to add credits'}), 500
            
    except Exception as e:
        logging.error(f"❌ Error verifying and processing credit purchase: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    logging.info(f"Webhook received - Signature: {sig_header[:50] if sig_header else 'None'}...")
    logging.info(f"Payload size: {len(payload)} bytes")
    
    try:
        event = None
        
        # Verify webhook signature and extract the event
        if endpoint_secret:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
            logging.info(f"Webhook signature verified successfully")
        else:
            # For testing without a webhook secret
            logging.warning("No webhook secret configured - parsing payload directly")
            try:
                event = json.loads(payload)
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON payload: {str(e)}")
                return jsonify({'error': 'Invalid payload'}), 400
        
        # Handle the event
        if event and event.get('type'):
            event_type = event['type']
            logging.info(f"Processing webhook event: {event_type}")
            
            # Handle checkout.session.completed event
            if event_type == 'checkout.session.completed':
                session = event['data']['object']
                logging.info(f"Checkout session completed - Session ID: {session.get('id')}")
                handle_checkout_session_completed(session)
            
            # Handle payment_intent.succeeded for credit purchases
            elif event_type == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                logging.info(f"Payment intent succeeded - PI ID: {payment_intent.get('id')}, Metadata: {payment_intent.get('metadata', {})}")
                handle_payment_intent_succeeded(payment_intent)
            
            # Handle customer.subscription events
            elif event_type == 'customer.subscription.created':
                subscription = event['data']['object']
                logging.info(f"Subscription created - Sub ID: {subscription.get('id')}")
                handle_subscription_created(subscription)
            
            elif event_type == 'customer.subscription.updated':
                subscription = event['data']['object']
                logging.info(f"Subscription updated - Sub ID: {subscription.get('id')}")
                handle_subscription_updated(subscription)
            
            elif event_type == 'customer.subscription.deleted':
                subscription = event['data']['object']
                logging.info(f"Subscription deleted - Sub ID: {subscription.get('id')}")
                handle_subscription_deleted(subscription)
            
            # Handle invoice events
            elif event_type == 'invoice.paid':
                invoice = event['data']['object']
                logging.info(f"Invoice paid - Invoice ID: {invoice.get('id')}")
                handle_invoice_paid(invoice)
            
            elif event_type == 'invoice.payment_failed':
                invoice = event['data']['object']
                logging.info(f"Invoice payment failed - Invoice ID: {invoice.get('id')}")
                handle_invoice_payment_failed(invoice)
            
            # Log other events
            else:
                logging.info(f"Unhandled event type: {event_type}")
            
            logging.info(f"Webhook event {event_type} processed successfully")
            return jsonify({'status': 'success'}), 200
        
        logging.error("Invalid event data received")
        return jsonify({'error': 'Invalid event data'}), 400
        
    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Webhook signature verification failed: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Helper functions for handling specific webhook events
def handle_checkout_session_completed(session):
    """
    Handle the checkout.session.completed event
    This event occurs when a customer completes the checkout process
    """
    try:
        # Get customer and subscription details
        customer_id = session.get('customer')
        subscription_id = session.get('subscription')
        client_reference_id = session.get('client_reference_id')  # This would be our user_id
        amount_total = session.get('amount_total', 0)  # Amount in cents
        
        if client_reference_id:
            # Find the user in our database
            user = User.query.get(client_reference_id)
            if user:
                # Update user subscription status
                user.is_premium = True
                user.subscription_status = 'active'  # Set subscription status
                user.stripe_customer_id = customer_id
                user.stripe_subscription_id = subscription_id
                
                # Set subscription dates
                from datetime import datetime
                user.subscription_start_date = datetime.utcnow()
                user.last_payment_date = datetime.utcnow()
                user.payment_failed = False  # Reset any previous payment failures
                
                # Add initial Elite credits if this is a new subscription
                try:
                    credit_service = CreditSystemService()
                    success, message, credits_added = credit_service.refill_monthly_credits(user.id)
                    if success:
                        logging.info(f"Added {credits_added} initial credits to user {client_reference_id}")
                    else:
                        logging.warning(f"Failed to add initial credits: {message}")
                except Exception as e:
                    logging.error(f"Error adding initial credits: {str(e)}")
                
                db.session.commit()
                logging.info(f"User {client_reference_id} subscription activated: {subscription_id}, amount: ${amount_total/100:.2f}")
            else:
                logging.warning(f"User not found for client_reference_id: {client_reference_id}")
        else:
            # Handle anonymous checkout or checkout without user reference
            logging.info(f"Checkout completed without user reference. Customer ID: {customer_id}")
            
    except Exception as e:
        logging.error(f"Error handling checkout.session.completed: {str(e)}")

def handle_payment_intent_succeeded(payment_intent):
    """Handle successful credit purchase payments"""
    try:
        metadata = payment_intent.get('metadata', {})
        payment_type = metadata.get('type')
        package_id = metadata.get('package_id')
        
        logging.info(f"Processing payment_intent.succeeded - PI: {payment_intent.get('id')}")
        logging.info(f"Payment intent metadata: {metadata}")
        
        # Enhanced flexible check - if we have package_id, treat it as credit purchase
        # This handles cases where payment_type might be 'subscription' but it's actually a credit purchase
        if package_id:
            payment_type = 'credit_purchase'
            logging.info(f"Found package_id in webhook metadata, treating as credit purchase: {package_id}")
        
        # Check if this is a credit purchase
        if payment_type == 'credit_purchase':
            user_id = metadata.get('user_id')
            
            logging.info(f"Credit purchase detected - Package: {package_id}, User: {user_id}")
            
            if package_id and user_id:
                # Process credit purchase
                credit_service = CreditSystemService()
                packages = credit_service.CREDIT_PACKAGES
                
                if package_id in packages:
                    package = packages[package_id]
                    total_credits = package['credits'] + package['bonus']
                    
                    logging.info(f"Processing credit package {package_id}: {total_credits} credits (${package['price']/100:.2f})")
                    
                    # Check user before processing
                    user = User.query.get(int(user_id))
                    if not user:
                        logging.error(f"User {user_id} not found for webhook processing")
                        return
                    
                    balance_before = user.credits_balance
                    logging.info(f"User {user_id} balance before: {balance_before}")
                    
                    success = credit_service.add_credits(
                        int(user_id),
                        total_credits,
                        'purchase',
                        {
                            'package_id': package_id,
                            'payment_intent_id': payment_intent['id'],
                            'price': package['price'],
                            'source': 'webhook'
                        }
                    )
                    
                    if success:
                        # Refresh user to get updated balance
                        db.session.refresh(user)
                        balance_after = user.credits_balance
                        
                        logging.info(f"✅ Webhook: Credits added successfully to user {user_id}: {balance_before} → {balance_after} (+{total_credits})")
                        
                        # Verify the balance actually increased
                        if balance_after == balance_before + total_credits:
                            logging.info(f"✅ Webhook: Balance verification passed")
                        else:
                            logging.warning(f"⚠️ Webhook: Balance verification failed - Expected {balance_before + total_credits}, got {balance_after}")
                        
                        db.session.commit()
                    else:
                        logging.error(f"❌ Webhook: Failed to add credits for user {user_id}")
                else:
                    logging.error(f"❌ Webhook: Invalid package_id: {package_id}. Available: {list(packages.keys())}")
            else:
                logging.warning(f"⚠️ Webhook: Missing package_id ({package_id}) or user_id ({user_id}) in payment intent metadata")
        else:
            logging.info(f"Non-credit purchase webhook - Payment type: {payment_type}")
        
    except Exception as e:
        logging.error(f"❌ Error handling payment_intent.succeeded webhook: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

def handle_subscription_created(subscription):
    """Handle the customer.subscription.created event"""
    try:
        customer_id = subscription.get('customer')
        subscription_id = subscription.get('id')
        status = subscription.get('status')
        
        # Find user by customer ID
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.stripe_subscription_id = subscription_id
            user.subscription_status = status
            db.session.commit()
            logging.info(f"Subscription created for user {user.id}: {subscription_id}")
        else:
            logging.warning(f"User not found for customer_id: {customer_id}")
            
    except Exception as e:
        logging.error(f"Error handling subscription.created: {str(e)}")

def handle_subscription_updated(subscription):
    """Handle the customer.subscription.updated event"""
    try:
        customer_id = subscription.get('customer')
        status = subscription.get('status')
        
        # Find user by customer ID
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.subscription_status = status
            # If subscription is active, ensure user has premium status
            if status == 'active':
                user.is_premium = True
            # If subscription is canceled or past_due, handle accordingly
            elif status in ['canceled', 'unpaid', 'past_due']:
                user.is_premium = False
            
            db.session.commit()
            logging.info(f"Subscription updated for user {user.id}: {status}")
        else:
            logging.warning(f"User not found for customer_id: {customer_id}")
            
    except Exception as e:
        logging.error(f"Error handling subscription.updated: {str(e)}")

def handle_subscription_deleted(subscription):
    """Handle the customer.subscription.deleted event"""
    try:
        customer_id = subscription.get('customer')
        
        # Find user by customer ID
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if user:
            user.is_premium = False
            user.subscription_status = 'canceled'
            db.session.commit()
            logging.info(f"Subscription canceled for user {user.id}")
        else:
            logging.warning(f"User not found for customer_id: {customer_id}")
            
    except Exception as e:
        logging.error(f"Error handling subscription.deleted: {str(e)}")

def handle_invoice_paid(invoice):
    """Handle the invoice.paid event"""
    try:
        customer_id = invoice.get('customer')
        subscription_id = invoice.get('subscription')
        amount_paid = invoice.get('amount_paid', 0)  # Amount in cents
        
        if customer_id and subscription_id:
            # Find user by customer ID
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if user:
                # Update payment status
                from datetime import datetime
                user.last_payment_date = datetime.utcnow()
                user.payment_failed = False  # Reset payment failure status
                
                # Ensure subscription status is active
                user.is_premium = True
                user.subscription_status = 'active'
                
                # Refill monthly credits for recurring subscription payments
                try:
                    credit_service = CreditSystemService()
                    success, message, credits_added = credit_service.refill_monthly_credits(user.id)
                    if success:
                        logging.info(f"Refilled {credits_added} monthly credits for user {user.id}")
                    else:
                        logging.warning(f"Failed to refill credits: {message}")
                except Exception as e:
                    logging.error(f"Error refilling monthly credits: {str(e)}")
                
                db.session.commit()
                logging.info(f"Invoice paid and credits refilled for user {user.id}, amount: ${amount_paid/100:.2f}")
            else:
                logging.warning(f"User not found for customer_id: {customer_id}")
                
    except Exception as e:
        logging.error(f"Error handling invoice.paid: {str(e)}")

def handle_invoice_payment_failed(invoice):
    """Handle the invoice.payment_failed event"""
    try:
        customer_id = invoice.get('customer')
        
        if customer_id:
            # Find user by customer ID
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
            if user:
                # Update payment status
                user.payment_failed = True
                db.session.commit()
                logging.info(f"Invoice payment failed for user {user.id}")
                
                # Here you might want to send an email notification to the user
                # about their failed payment
            else:
                logging.warning(f"User not found for customer_id: {customer_id}")
                
    except Exception as e:
        logging.error(f"Error handling invoice.payment_failed: {str(e)}")