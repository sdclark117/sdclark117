# Deploying to Render.com

This guide will help you deploy the Business Lead Finder web application to Render.com for free.

## Step 1: Sign Up for Render

1. Go to [Render.com](https://render.com/)
2. Click "Sign Up"
3. You can sign up with your GitHub account or email
4. Verify your email if required

## Step 2: Connect Your Repository

1. In your Render dashboard, click "New +"
2. Select "Web Service"
3. Connect your GitHub repository
   - If you haven't already, push your code to GitHub
   - Select the repository containing your application

## Step 3: Configure Your Web Service

1. Fill in the following details:
   - Name: `business-lead-finder` (or your preferred name)
   - Environment: `Python`
   - Region: Choose the closest to your users
   - Branch: `main` (or your default branch)
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`

2. Add Environment Variables:
   - Click "Environment"
   - Add your Google Maps API key:
     - Key: `GOOGLE_MAPS_API_KEY`
     - Value: Your API key

3. Click "Create Web Service"

## Step 4: Wait for Deployment

1. Render will automatically:
   - Clone your repository
   - Install dependencies
   - Build your application
   - Deploy it

2. You can monitor the deployment in the "Logs" tab

## Step 5: Access Your Application

1. Once deployed, your application will be available at:
   `https://business-lead-finder.onrender.com`
   (or whatever name you chose)

2. Share this URL with anyone to access your application

## Free Tier Limitations

The free tier includes:
- 750 hours of runtime per month
- Automatic sleep after 15 minutes of inactivity
- 512 MB RAM
- Shared CPU

## Troubleshooting

If you encounter issues:

1. Check the deployment logs in Render dashboard
2. Verify your environment variables
3. Make sure all dependencies are in requirements.txt
4. Check that your application works locally

## Security Considerations

1. Keep your Google Maps API key secure
2. Enable API key restrictions in Google Cloud Console
3. Set up proper CORS policies
4. Consider adding rate limiting

## Maintenance

1. Monitor your application logs
2. Keep your dependencies updated
3. Check your usage in the Render dashboard
4. Back up your data regularly

## Support

If you need help:
1. Check Render's documentation
2. Visit Render's community forums
3. Contact Render support

## Upgrading (Optional)

If you need more resources:
1. Go to your web service settings
2. Click "Change Plan"
3. Choose a paid plan that fits your needs 