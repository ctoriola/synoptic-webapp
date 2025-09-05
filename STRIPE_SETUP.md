# Stripe Payment Integration Setup Guide

## Prerequisites
1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe Dashboard

## Step 1: Get Stripe API Keys

1. Log into your Stripe Dashboard
2. Go to **Developers** > **API keys**
3. Copy your **Publishable key** and **Secret key**
4. For webhooks, you'll also need the **Webhook signing secret**

## Step 2: Environment Variables

Add these variables to your `.env` file:

```bash
# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Stripe Price IDs (you'll create these in Step 4)
STRIPE_BASIC_PRICE_ID=price_basic_monthly_id
STRIPE_PRO_PRICE_ID=price_pro_monthly_id
```

## Step 3: Create Products and Prices in Stripe

1. Go to **Products** in your Stripe Dashboard
2. Create two products:

### Basic Plan Product
- **Name**: "Synoptic Basic Plan"
- **Description**: "10 AI pitch deck generations per month"
- **Price**: $9.00 USD
- **Billing**: Monthly recurring
- Copy the **Price ID** (starts with `price_`)

### Pro Plan Product
- **Name**: "Synoptic Pro Plan" 
- **Description**: "50 AI pitch deck generations per month"
- **Price**: $29.00 USD
- **Billing**: Monthly recurring
- Copy the **Price ID** (starts with `price_`)

## Step 4: Set up Webhooks

1. Go to **Developers** > **Webhooks** in Stripe Dashboard
2. Click **Add endpoint**
3. Set endpoint URL to: `https://yourdomain.com/api/stripe/webhook`
4. Select these events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.deleted`
5. Copy the **Signing secret** (starts with `whsec_`)

## Step 5: Update Environment Variables

Update your `.env` file with the actual Price IDs:

```bash
STRIPE_BASIC_PRICE_ID=price_1234567890abcdef  # Replace with actual Basic price ID
STRIPE_PRO_PRICE_ID=price_0987654321fedcba   # Replace with actual Pro price ID
```

## Step 6: Test the Integration

1. Use Stripe's test mode initially
2. Test card numbers:
   - Success: `4242424242424242`
   - Declined: `4000000000000002`
3. Use any future expiry date and any 3-digit CVC

## Step 7: Go Live

1. Switch to live mode in Stripe Dashboard
2. Update environment variables with live keys
3. Update webhook endpoint to production URL
4. Test with real payment methods

## Security Notes

- Never commit API keys to version control
- Use environment variables for all sensitive data
- Validate webhook signatures to prevent fraud
- Use HTTPS for all payment-related endpoints

## Troubleshooting

### Common Issues:
1. **Webhook signature verification fails**: Check that `STRIPE_WEBHOOK_SECRET` matches your endpoint
2. **Payment doesn't complete**: Check webhook events are properly configured
3. **User not upgraded**: Ensure webhook handler updates user account properly

### Testing Webhooks Locally:
Use Stripe CLI to forward webhooks to localhost:
```bash
stripe listen --forward-to localhost:5000/api/stripe/webhook
```
