# 🚀 Synoptic Complete Setup Guide

Complete guide for setting up and deploying Synoptic - AI-powered pitch deck generator.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Firebase Setup](#firebase-setup)
3. [GitHub OAuth Setup](#github-oauth-setup)
4. [Hugging Face Models Setup](#hugging-face-models-setup)
5. [Stripe Payment Integration](#stripe-payment-integration)
6. [Environment Variables](#environment-variables)
7. [Local Development](#local-development)
8. [Deployment](#deployment)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:

- Python 3.8+
- pip (Python package manager)
- Git
- A Firebase account
- A GitHub account
- A Hugging Face account
- A Stripe account (for payments)
- Google AI API key

---

## Firebase Setup

### 1. Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **"Create a project"**
3. Project name: `synoptic-saas` (or your preferred name)
4. Enable Google Analytics: Optional (recommended)
5. Choose Analytics account: Default or create new

### 2. Enable Firestore Database

1. In Firebase Console, go to **"Firestore Database"**
2. Click **"Create database"**
3. Security rules: Start in **test mode** (we'll secure later)
4. Location: Choose closest to your users (e.g., `us-central1`)

### 3. Generate Service Account Key

1. Go to **Project Settings** (gear icon)
2. Click **"Service accounts"** tab
3. Click **"Generate new private key"**
4. Download the JSON file (keep it secure!)
5. You'll need these values for environment variables

### 4. Firestore Security Rules (Production)

After testing, update Firestore security rules:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Users can only access their own projects
    match /projects/{projectId} {
      allow read, write: if request.auth != null && 
        resource.data.user_id == request.auth.uid;
    }
  }
}
```

### Firebase Free Tier Limits

| Resource | Free Tier | Paid Plans Start |
|----------|-----------|------------------|
| **Reads** | 50,000/day | $0.06/100K |
| **Writes** | 20,000/day | $0.18/100K |
| **Deletes** | 20,000/day | $0.02/100K |
| **Storage** | 1GB | $0.18/GB/month |
| **Bandwidth** | 10GB/month | $0.12/GB |

---

## GitHub OAuth Setup

### 1. Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **"New OAuth App"**
3. Fill in the application details:
   - **Application name**: `Synoptic` (or your preferred name)
   - **Homepage URL**: Your deployed app URL (e.g., `https://your-app.vercel.app`)
   - **Application description**: `AI-powered pitch deck generator`
   - **Authorization callback URL**: `https://your-app.vercel.app/auth/github/callback`

### 2. Get OAuth Credentials

After creating the app:
1. Copy the **Client ID**
2. Generate a **Client Secret** and copy it
3. Keep these credentials secure

### 3. Callback URLs for Different Environments

- **Local Development**: `http://localhost:5000/auth/github/callback`
- **Production**: `https://your-domain.com/auth/github/callback`

### 4. OAuth Scopes

The app requests these scopes:
- `user:email` - To get user's email address
- `repo` - To access repository information for pitch deck generation

---

## Hugging Face Models Setup

### Current Implementation: Gradio Spaces

The app uses your Hugging Face Spaces with Gradio client for model inference.

### 1. Get Hugging Face API Token

1. Go to https://huggingface.co/settings/tokens
2. Create a new token with **write** access
3. Copy your token (starts with `hf_...`)

### 2. Your Hugging Face Spaces

The app is configured to use these spaces:

```python
MISTRAL_URL = 'https://huggingface.co/spaces/charl33zy/mistralai-Mistral-7B-Instruct-v0.2'
ZEPHYR_URL = 'https://huggingface.co/spaces/charl33zy/HuggingFaceH4-zephyr-7b-alpha'
```

### 3. Gradio Client Implementation

The app uses the official `gradio_client` library:

```python
from gradio_client import Client

# Connect to Space
client = Client(space_url, hf_token=HF_TOKEN)

# Make prediction
result = client.predict(prompt, api_name="/predict")
```

### 4. Important Notes

- **Space Status**: Spaces can go to sleep after inactivity
- **First Call**: May take 5-10 seconds to wake up
- **Subsequent Calls**: Fast (~2-3 seconds each)
- **Config Errors**: If you see "Could not fetch config", your Space may not have a proper Gradio interface

### Troubleshooting Spaces

If your Spaces are not working:

1. **Visit your Spaces** and verify they have a Gradio interface
2. **Check Space status** - should be "Running" or will auto-wake
3. **Verify Space URLs** match exactly what's in the code
4. **Check logs** for detailed error messages

---

## Stripe Payment Integration

### 1. Get Stripe API Keys

1. Log into your [Stripe Dashboard](https://stripe.com)
2. Go to **Developers** > **API keys**
3. Copy your **Publishable key** and **Secret key**

### 2. Create Products and Prices

In your Stripe Dashboard, go to **Products** and create:

#### Basic Plan
- **Name**: "Synoptic Basic Plan"
- **Description**: "10 AI pitch deck generations per month"
- **Price**: $9.00 USD
- **Billing**: Monthly recurring
- Copy the **Price ID** (starts with `price_`)

#### Pro Plan
- **Name**: "Synoptic Pro Plan" 
- **Description**: "50 AI pitch deck generations per month"
- **Price**: $29.00 USD
- **Billing**: Monthly recurring
- Copy the **Price ID** (starts with `price_`)

### 3. Set up Webhooks

1. Go to **Developers** > **Webhooks**
2. Click **Add endpoint**
3. Set endpoint URL to: `https://yourdomain.com/api/stripe/webhook`
4. Select these events:
   - `checkout.session.completed`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
   - `customer.subscription.deleted`
5. Copy the **Signing secret** (starts with `whsec_`)

### 4. Test Cards (Test Mode)

- **Success**: `4242424242424242`
- **Declined**: `4000000000000002`
- Use any future expiry date and any 3-digit CVC

---

## Environment Variables

Create a `.env` file in your project root with these variables:

```bash
# Flask Configuration
SECRET_KEY=your_secret_key_here_generate_with_python_secrets
FLASK_ENV=production

# Google AI (Gemini)
GOOGLE_API_KEY=your_google_ai_api_key_here

# Firebase Configuration
FIREBASE_PROJECT_ID=synoptic-saas
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----"
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-xxxxx@synoptic-saas.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here

# Hugging Face
HF_API_TOKEN=hf_your_huggingface_token_here

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here
STRIPE_BASIC_PRICE_ID=price_basic_monthly_id
STRIPE_PRO_PRICE_ID=price_pro_monthly_id

# OpenAI (Optional - for fallback)
OPENAI_API_KEY=sk-your_openai_key_here
```

### For Vercel/Netlify Deployment

Add all these environment variables in your deployment platform's settings:

1. Go to your project settings
2. Find **Environment Variables** section
3. Add each variable individually
4. Redeploy after adding variables

---

## Local Development

### 1. Clone and Install

```bash
# Clone repository
git clone https://github.com/ctoriola/synoptic-webapp.git
cd synoptic-webapp

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

```bash
# Create .env file
cp .env.example .env

# Edit .env with your actual credentials
# Use a text editor to fill in all the values
```

### 3. Run the Application

```bash
# Run Flask app
python app.py

# App will be available at http://localhost:5000
```

---

## Deployment

### Vercel Deployment (Recommended)

1. **Install Vercel CLI** (optional):
```bash
npm install -g vercel
```

2. **Deploy via GitHub Integration**:
   - Connect your GitHub repository to Vercel
   - Vercel will auto-detect Flask app
   - Add environment variables in Vercel dashboard
   - Deploy!

3. **Configuration Files**:
   - `vercel.json` - Already configured for Flask
   - `requirements.txt` - All Python dependencies

### Netlify Deployment

1. **Configuration**:
   - `netlify.toml` - Already configured
   - Add environment variables in Netlify dashboard

2. **Deploy**:
   - Connect GitHub repository
   - Configure build settings
   - Deploy!

---

## Troubleshooting

### Common Issues

#### 1. "Could not fetch config" Error (Hugging Face Spaces)

**Cause**: Your Spaces don't have a proper Gradio API configuration

**Solution**:
- Visit your Spaces and verify they have a Gradio interface
- Check if Spaces are "Running" (they may need to wake up)
- Verify Space URLs match exactly what's in the code
- Check logs for detailed error messages

#### 2. GitHub OAuth 404 Error

**Cause**: OAuth app configuration doesn't match

**Solution**:
- Verify callback URL in GitHub matches exactly (including protocol)
- Check that `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` are correct
- Ensure OAuth app exists in your GitHub settings

#### 3. Firebase Connection Error

**Cause**: Invalid Firebase credentials

**Solution**:
- Verify all Firebase environment variables are set correctly
- Check that the private key includes `\n` for line breaks
- Ensure service account has proper permissions

#### 4. Stripe Webhook Signature Verification Fails

**Cause**: Incorrect webhook secret

**Solution**:
- Verify `STRIPE_WEBHOOK_SECRET` matches your endpoint
- Check webhook is configured for the correct events
- Ensure webhook URL matches your deployed app

#### 5. "Pitch Generation Failed" Error

**Cause**: Hugging Face Spaces not responding

**Solution**:
- Check Vercel logs for detailed error messages
- Verify HF_API_TOKEN is valid
- Check if Spaces are accessible from your deployment region
- Consider using OpenAI fallback (add OPENAI_API_KEY)

### Testing Webhooks Locally

Use Stripe CLI to forward webhooks to localhost:

```bash
stripe listen --forward-to localhost:5000/api/stripe/webhook
```

### Checking Logs

**Vercel**:
```bash
vercel logs --follow
```

**Local**:
Check terminal output where Flask is running

---

## Security Best Practices

1. ✅ **Never commit secrets** to version control
2. ✅ **Use environment variables** for all sensitive data
3. ✅ **Rotate secrets regularly** in production
4. ✅ **Use different OAuth apps** for development and production
5. ✅ **Enable Firebase security rules** after testing
6. ✅ **Validate webhook signatures** to prevent fraud
7. ✅ **Use HTTPS** for all payment-related endpoints

---

## Support

For issues and questions:

1. Check this guide first
2. Review error logs for detailed messages
3. Open an issue on GitHub
4. Contact the development team

---

## Next Steps

After completing setup:

1. ✅ Test local development
2. ✅ Deploy to staging environment
3. ✅ Test all features (auth, generation, payments)
4. ✅ Configure production Firebase security rules
5. ✅ Switch Stripe to live mode
6. ✅ Deploy to production
7. ✅ Monitor logs and usage

---

**Setup Time Estimate**: 30-45 minutes

**Your Synoptic app will be live and ready for users!** 🚀
