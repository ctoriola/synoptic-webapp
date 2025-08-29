# GitHub OAuth Setup Guide

To enable GitHub OAuth authentication in Synoptic, you need to create a GitHub OAuth App and configure the environment variables.

## Step 1: Create GitHub OAuth App

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the application details:
   - **Application name**: `Synoptic` (or your preferred name)
   - **Homepage URL**: Your deployed app URL (e.g., `https://your-app.vercel.app`)
   - **Application description**: `AI-powered pitch deck generator for GitHub repositories`
   - **Authorization callback URL**: `https://your-app.vercel.app/auth/github/callback`

## Step 2: Get OAuth Credentials

After creating the app:
1. Copy the **Client ID**
2. Generate a **Client Secret** and copy it
3. Keep these credentials secure

## Step 3: Configure Environment Variables

Add these variables to your `.env` file:

```env
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here
```

## Step 4: Deploy Configuration

For production deployment (Vercel/Netlify):
1. Add the environment variables in your deployment platform's settings
2. Ensure the callback URL matches your deployed domain

## Callback URLs for Different Environments

- **Local Development**: `http://localhost:5000/auth/github/callback`
- **Production**: `https://your-domain.com/auth/github/callback`

## Troubleshooting

### 404 Error on GitHub
- Verify the OAuth app exists in your GitHub settings
- Check that the callback URL in GitHub matches exactly (including protocol)
- Ensure environment variables are set correctly

### "OAuth is not init with Flask app" Error
- This should be fixed in the latest version
- Ensure `init_oauth(app)` is called in `app.py`

### Missing Scopes
The app requests these scopes:
- `user:email` - To get user's email address
- `repo` - To access repository information for pitch deck generation

## Security Notes

- Never commit OAuth credentials to version control
- Use different OAuth apps for development and production
- Regularly rotate client secrets in production
