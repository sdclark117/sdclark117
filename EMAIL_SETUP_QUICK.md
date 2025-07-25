# Quick Email Setup Guide

## 🚨 Email Verification Issue Fixed

The "failed to send email" error occurs because Gmail is not configured. Here's how to fix it:

### Step 1: Create .env file

Create a file named `.env` in your project root directory with these contents:

```env
# Gmail Configuration
GMAIL_USERNAME=your.email@gmail.com
GMAIL_APP_PASSWORD=your-16-character-app-password

# Other Configuration  
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
SECRET_KEY=your-secret-key-here
FLASK_ENV=development
FLASK_DEBUG=1
```

### Step 2: Set up Gmail App Password

1. **Go to your Google Account**: https://myaccount.google.com/
2. **Enable 2-Factor Authentication** (if not already enabled)
3. **Generate App Password**:
   - Go to Security → App passwords
   - Select "Mail" and "Other"
   - Name it "Business Lead Finder"
   - Copy the 16-character password
4. **Update your .env file** with your actual Gmail and app password

### Step 3: Restart the Application

```bash
# Stop the current app (Ctrl+C)
# Then restart:
python app.py
```

### Step 4: Test Email Verification

1. Go to `http://localhost:5000`
2. Login with your basic plan user
3. Click your name → Profile
4. Click "Resend Verification Email"
5. Check your email for the verification link

### Troubleshooting

**If you still get errors:**
- Check that your `.env` file is in the project root
- Verify your Gmail username and app password are correct
- Make sure 2-Factor Authentication is enabled on your Gmail account
- Check the console logs for specific error messages

**Alternative: Skip Email Verification (for testing)**
If you want to test without email setup, you can manually verify a user in the database or modify the code to auto-verify users.

### Need Help?

See the full `GMAIL_SETUP.md` file for detailed instructions. 