#!/usr/bin/env python3

"""
One-time script to update subscription end dates for all active subscriptions.
This script fetches the current_period_end from Stripe for all users with active subscriptions
and updates the subscription_end_date field in the database.
"""

import os
import sys
import stripe
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add the current directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the app and models
from app import create_app, db
from app.models.user import User

def update_subscription_dates():
    """Update subscription end dates for all active subscriptions"""
    app = create_app()
    with app.app_context():
        # Get all users with active subscriptions
        users = User.query.filter(
            User.stripe_subscription_id.isnot(None)
        ).all()
        
        logging.info(f"Found {len(users)} users with subscription IDs")
        
        # Set up Stripe
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        if not stripe.api_key:
            logging.error("STRIPE_SECRET_KEY environment variable not set")
            return
        
        updated_count = 0
        error_count = 0
        
        for user in users:
            try:
                logging.info(f"Processing user {user.id} with subscription {user.stripe_subscription_id}")
                
                # Get subscription from Stripe
                stripe_sub = stripe.Subscription.retrieve(user.stripe_subscription_id)
                
                # Update the subscription end date
                if stripe_sub and hasattr(stripe_sub, 'current_period_end'):
                    current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
                    
                    # Update the user's subscription end date
                    user.subscription_end_date = current_period_end
                    
                    # Also update subscription status if needed
                    if user.subscription_status != stripe_sub.status:
                        user.subscription_status = stripe_sub.status
                        logging.info(f"Updated subscription status to {stripe_sub.status}")
                    
                    logging.info(f"Updated user {user.id}: end date = {current_period_end}")
                    updated_count += 1
                else:
                    logging.warning(f"No current_period_end found for subscription {user.stripe_subscription_id}")
                
            except Exception as e:
                logging.error(f"Error updating user {user.id}: {str(e)}")
                error_count += 1
        
        # Commit all changes
        if updated_count > 0:
            db.session.commit()
            logging.info(f"Successfully updated {updated_count} users")
        else:
            logging.info("No users were updated")
        
        if error_count > 0:
            logging.warning(f"{error_count} errors occurred during processing")

if __name__ == "__main__":
    update_subscription_dates() 