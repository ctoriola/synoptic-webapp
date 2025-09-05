import stripe
import os
from flask import Blueprint, request, jsonify, redirect, url_for, session
from flask_login import login_required, current_user
from firebase_models import User
import logging

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

stripe_bp = Blueprint('stripe', __name__)

# Plan configuration
PLANS = {
    'basic': {
        'name': 'Basic Plan',
        'price_id': os.getenv('STRIPE_BASIC_PRICE_ID'),
        'tokens': 10,
        'price': 9.00
    },
    'pro': {
        'name': 'Pro Plan', 
        'price_id': os.getenv('STRIPE_PRO_PRICE_ID'),
        'tokens': 50,
        'price': 29.00
    }
}

@stripe_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    """Create a Stripe checkout session for plan upgrade"""
    try:
        data = request.get_json()
        plan_type = data.get('plan_type')
        
        if plan_type not in PLANS:
            return jsonify({'error': 'Invalid plan type'}), 400
            
        plan = PLANS[plan_type]
        
        # Create or get Stripe customer
        customer_id = current_user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.username,
                metadata={
                    'user_id': current_user.id
                }
            )
            customer_id = customer.id
            
            # Update user with Stripe customer ID
            current_user.stripe_customer_id = customer_id
            current_user.save()
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': plan['price_id'],
                'quantity': 1,
            }],
            mode='subscription',
            success_url=url_for('main.pricing', _external=True) + '?success=true&plan=' + plan_type,
            cancel_url=url_for('main.pricing', _external=True) + '?canceled=true',
            metadata={
                'user_id': current_user.id,
                'plan_type': plan_type
            }
        )
        
        return jsonify({'checkout_url': checkout_session.url})
        
    except Exception as e:
        logging.error(f"Stripe checkout error: {str(e)}")
        return jsonify({'error': 'Failed to create checkout session'}), 500

@stripe_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        logging.error(f"Invalid payload: {e}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logging.error(f"Invalid signature: {e}")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_successful_payment(session)
        
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        handle_subscription_renewal(invoice)
        
    elif event['type'] == 'invoice.payment_failed':
        invoice = event['data']['object']
        handle_payment_failed(invoice)
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_cancelled(subscription)
    
    return jsonify({'status': 'success'})

def handle_successful_payment(session):
    """Handle successful payment from checkout session"""
    try:
        user_id = session['metadata']['user_id']
        plan_type = session['metadata']['plan_type']
        
        user = User.get(user_id)
        if user:
            plan = PLANS[plan_type]
            
            # Update user account
            user.account_tier = plan_type
            user.tokens = plan['tokens']
            user.stripe_subscription_id = session.get('subscription')
            user.save()
            
            logging.info(f"User {user_id} upgraded to {plan_type} plan")
            
    except Exception as e:
        logging.error(f"Error handling successful payment: {str(e)}")

def handle_subscription_renewal(invoice):
    """Handle monthly subscription renewal"""
    try:
        customer_id = invoice['customer']
        
        # Find user by Stripe customer ID
        user = User.get_by_stripe_customer_id(customer_id)
        if user and user.account_tier in PLANS:
            plan = PLANS[user.account_tier]
            
            # Reset tokens for the new billing period
            user.tokens = plan['tokens']
            user.save()
            
            logging.info(f"Tokens reset for user {user.id} - {plan['tokens']} tokens")
            
    except Exception as e:
        logging.error(f"Error handling subscription renewal: {str(e)}")

def handle_payment_failed(invoice):
    """Handle failed payment"""
    try:
        customer_id = invoice['customer']
        
        # Find user by Stripe customer ID
        user = User.get_by_stripe_customer_id(customer_id)
        if user:
            # You might want to send an email notification here
            logging.warning(f"Payment failed for user {user.id}")
            
    except Exception as e:
        logging.error(f"Error handling payment failure: {str(e)}")

def handle_subscription_cancelled(subscription):
    """Handle subscription cancellation"""
    try:
        customer_id = subscription['customer']
        
        # Find user by Stripe customer ID
        user = User.get_by_stripe_customer_id(customer_id)
        if user:
            # Downgrade to free plan
            user.account_tier = 'free'
            user.tokens = 3  # Free plan tokens
            user.stripe_subscription_id = None
            user.save()
            
            logging.info(f"User {user.id} downgraded to free plan")
            
    except Exception as e:
        logging.error(f"Error handling subscription cancellation: {str(e)}")

@stripe_bp.route('/cancel-subscription', methods=['POST'])
@login_required
def cancel_subscription():
    """Cancel user's subscription"""
    try:
        if not current_user.stripe_subscription_id:
            return jsonify({'error': 'No active subscription found'}), 400
            
        # Cancel the subscription at period end
        stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        return jsonify({'success': True, 'message': 'Subscription will be cancelled at the end of the billing period'})
        
    except Exception as e:
        logging.error(f"Error cancelling subscription: {str(e)}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500

@stripe_bp.route('/customer-portal', methods=['POST'])
@login_required
def customer_portal():
    """Create Stripe customer portal session"""
    try:
        if not current_user.stripe_customer_id:
            return jsonify({'error': 'No Stripe customer found'}), 400
            
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=url_for('main.pricing', _external=True)
        )
        
        return jsonify({'portal_url': portal_session.url})
        
    except Exception as e:
        logging.error(f"Error creating customer portal: {str(e)}")
        return jsonify({'error': 'Failed to create customer portal'}), 500
