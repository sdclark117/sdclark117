# Google Maps API Key Security Guide

## Urgent: Secure Your API Keys

You received an email from Google Maps Platform about securing unrestricted API keys. This guide will help you properly restrict your API keys to prevent abuse and extra billing charges.

## Step 1: Access Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project that contains the Google Maps API key
3. Navigate to **"APIs & Services" > "Credentials"**

## Step 2: Find Your API Key

1. In the Credentials page, locate your Google Maps API key
2. Click on the API key to edit its settings

## Step 3: Apply Restrictions

### Application Restrictions
1. **HTTP referrers (web sites)**: Add your domain(s)
   - For local development: `http://localhost:5000/*`
   - For production: `https://yourdomain.com/*`
   - For Render deployment: `https://your-app-name.onrender.com/*`

### API Restrictions
1. **Restrict key**: Select "Restrict key"
2. **API restrictions**: Select "Restrict key to selected APIs"
3. **Select APIs**: Choose only the APIs you need:
   - **Maps JavaScript API** (for the map display)
   - **Places API** (for business search)
   - **Geocoding API** (for address to coordinates conversion)

## Step 4: Monitor Usage

1. Go to **"APIs & Services" > "Dashboard"**
2. Monitor your API usage and billing
3. Set up billing alerts in Google Cloud Console

## Step 5: Environment Variables

Ensure your API key is stored securely in environment variables:

### Local Development (.env file)
```env
GOOGLE_MAPS_API_KEY=your-restricted-api-key-here
```

### Production (Render/Heroku/etc.)
Set the environment variable in your deployment platform:
- Key: `GOOGLE_MAPS_API_KEY`
- Value: Your restricted API key

## Security Best Practices

### 1. Never Commit API Keys
- ✅ Use environment variables
- ❌ Never hardcode in source code
- ❌ Never commit to version control

### 2. Use Different Keys for Different Environments
- Development key (with localhost restrictions)
- Production key (with your domain restrictions)

### 3. Regular Monitoring
- Check API usage weekly
- Set up billing alerts
- Monitor for unusual activity

### 4. Key Rotation
- Regularly rotate your API keys
- Update environment variables when rotating

## Verification Steps

1. **Test your application** after applying restrictions
2. **Verify the map loads** on your website
3. **Test business search functionality**
4. **Check that geocoding works** for address searches

## Troubleshooting

### Common Issues

**"This API project is not authorized"**
- Make sure you've enabled the required APIs in Google Cloud Console

**"Referrer not allowed"**
- Check that your domain is properly added to HTTP referrers
- Include both `http://` and `https://` versions if needed

**"API key not valid"**
- Verify the API key is correctly set in environment variables
- Check that the key hasn't been accidentally restricted too much

## Additional Security Measures

### 1. Enable Billing Alerts
1. Go to Google Cloud Console > Billing
2. Set up budget alerts
3. Configure email notifications

### 2. Monitor API Usage
1. Go to APIs & Services > Dashboard
2. Check usage by API
3. Set up monitoring for unusual spikes

### 3. Consider API Quotas
1. Set daily quotas for your APIs
2. Monitor quota usage
3. Adjust as needed

## Emergency Contacts

If you need immediate assistance:
- Google Cloud Support: https://cloud.google.com/support
- Google Maps Platform Support: https://developers.google.com/maps/support

## Next Steps

1. **Immediately** apply the restrictions above
2. **Test** your application thoroughly
3. **Monitor** usage for the next few days
4. **Set up** billing alerts
5. **Document** your API key management process

Remember: The goal is to allow your application to work while preventing unauthorized usage that could lead to unexpected charges. 