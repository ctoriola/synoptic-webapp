import stripe
import os
from flask import Blueprint, request, jsonify, redirect, url_for, session
from flask_login import login_required, current_user
from firebase_models import User
import logging

# Initialize Stripe with explicit configuration
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Set Stripe API key
stripe.api_key = STRIPE_SECRET_KEY

# Validate Stripe configuration at startup
if not STRIPE_SECRET_KEY:
    logging.error("STRIPE_SECRET_KEY environment variable not set")
if not STRIPE_PUBLISHABLE_KEY:
    logging.error("STRIPE_PUBLISHABLE_KEY environment variable not set")
if not STRIPE_WEBHOOK_SECRET:
    logging.error("STRIPE_WEBHOOK_SECRET environment variable not set")

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
        # Debug: Log environment variables (safely)
        logging.info(f"Stripe API Key configured: {bool(stripe.api_key)}")
        logging.info(f"Webhook secret configured: {bool(os.getenv('STRIPE_WEBHOOK_SECRET'))}")
        
        # Validate Stripe configuration
        if not stripe.api_key:
            return jsonify({'error': 'Stripe not configured properly'}), 500
            
        data = request.get_json()
        plan_type = data.get('plan_type')
        
        if plan_type not in PLANS:
            return jsonify({'error': 'Invalid plan type'}), 400
            
        plan = PLANS[plan_type]
        
        if not plan['price_id']:
            return jsonify({'error': f'Price ID not configured for {plan_type} plan'}), 500
        
        logging.info(f"Processing checkout for plan: {plan_type}, price_id: {plan['price_id']}")
        logging.info("About to handle Stripe customer creation/retrieval")
        
        # Create or get Stripe customer
        customer_id = current_user.stripe_customer_id
        if not customer_id:
            logging.info("Creating new Stripe customer")
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.username,
                metadata={
                    'user_id': current_user.id
                }
            )
            customer_id = customer.id
            logging.info(f"Stripe customer created: {customer_id}")
            
            # Update user with Stripe customer ID
            try:
                current_user.stripe_customer_id = customer_id
                current_user.save()
                logging.info("User updated with Stripe customer ID")
            except Exception as save_error:
                logging.error(f"Failed to save user with Stripe customer ID: {str(save_error)}")
                # Continue anyway, we have the customer_id
        else:
            logging.info(f"Using existing Stripe customer: {customer_id}")
        
        # Validate price_id format (should start with 'price_' not 'prod_')
        price_id = plan['price_id']
        logging.info(f"About to validate price_id: {price_id}")
        if not price_id or not price_id.startswith('price_'):
            logging.error(f"Invalid price_id format: {price_id}. Must start with 'price_'")
            return jsonify({'error': f'Invalid price configuration for {plan_type} plan. Expected price ID, got: {price_id}'}), 500

        logging.info("Price ID validation passed, proceeding to checkout session creation")
        # Create checkout session with step-by-step debugging
        try:
            logging.info(f"Creating checkout session for customer: {customer_id}, plan: {plan_type}, price_id: {price_id}")
            
            # Use request.host_url to build URLs instead of url_for to avoid context issues
            try:
                base_url = request.host_url.rstrip('/')
                success_url = f"{base_url}/pricing?success=true&plan={plan_type}"
                cancel_url = f"{base_url}/pricing?canceled=true"
                logging.info(f"URLs generated - Success: {success_url}, Cancel: {cancel_url}")
            except Exception as url_error:
                logging.error(f"URL generation failed: {str(url_error)}")
                return jsonify({'error': f'URL generation failed: {str(url_error)}'}), 500
            
            # Create session parameters step by step
            session_params = {}
            session_params['customer'] = customer_id
            session_params['payment_method_types'] = ['card']
            session_params['line_items'] = [{'price': price_id, 'quantity': 1}]
            session_params['mode'] = 'subscription'
            session_params['success_url'] = success_url
            session_params['cancel_url'] = cancel_url
            session_params['metadata'] = {'user_id': str(current_user.id), 'plan_type': plan_type}
            
            logging.info(f"Session params prepared: {session_params}")
            
            # Create the checkout session with minimal parameters first
            logging.info("About to call stripe.checkout.Session.create")
            
            # Try with absolute minimal parameters to isolate the issue
            minimal_params = {
                'payment_method_types': ['card'],
                'line_items': [{'price': price_id, 'quantity': 1}],
                'mode': 'subscription',
                'success_url': success_url,
                'cancel_url': cancel_url
            }
            
            logging.info(f"Minimal params: {minimal_params}")
            checkout_session = stripe.checkout.Session.create(**minimal_params)
            logging.info(f"Checkout session created successfully: {checkout_session.id}")
            
        except stripe.error.InvalidRequestError as e:
            logging.error(f"Stripe invalid request: {str(e)}")
            return jsonify({'error': f'Invalid request to Stripe: {str(e)}'}), 400
        except stripe.error.AuthenticationError as e:
            logging.error(f"Stripe authentication error: {str(e)}")
            return jsonify({'error': 'Stripe authentication failed'}), 500
        except Exception as e:
            logging.error(f"Unexpected error during checkout session creation: {str(e)}")
            import traceback
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return jsonify({'error': f'Checkout session creation failed: {str(e)}'}), 500
        
        return jsonify({'checkout_url': checkout_session.url})
        
    except Exception as e:
        logging.error(f"Stripe checkout error: {str(e)}")
        return jsonify({'error': 'Failed to create checkout session'}), 500

@stripe_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks"""
    if not STRIPE_WEBHOOK_SECRET:
        logging.error("STRIPE_WEBHOOK_SECRET environment variable not set")
        return jsonify({'error': 'Webhook secret not configured'}), 500
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
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
