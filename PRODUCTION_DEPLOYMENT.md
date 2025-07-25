# Production Deployment Guide - Email Verification

## 🚀 **Deploying to Production on Render**

Your application is ready for production deployment with email verification working for all customers.

### **Step 1: Set Up Gmail for Production**

1. **Create a Business Gmail Account** (recommended):
   - Go to [Google Workspace](https://workspace.google.com/)
   - Create a business email like `noreply@yourbusiness.com`
   - Or use a regular Gmail account

2. **Enable 2-Factor Authentication**:
   - Go to your Google Account settings
   - Enable 2-Step Verification

3. **Generate App Password**:
   - Go to Security → App passwords
   - Select "Mail" and "Other"
   - Name it "Business Lead Finder Production"
   - Copy the 16-character password

### **Step 2: Configure Render Environment Variables**

In your Render dashboard, set these environment variables:

**Required for Email:**
```
GMAIL_USERNAME=your-business-email@gmail.com
GMAIL_APP_PASSWORD=your-16-character-app-password
```

**Already Configured:**
```
FLASK_ENV=production
SECRET_KEY=auto-generated
GOOGLE_MAPS_API_KEY=your-key
STRIPE_KEYS=your-keys
```

### **Step 3: Deploy to Production**

1. **Push your changes to GitHub**:
   ```bash
   git add .
   git commit -m "Production email verification ready"
   git push origin main
   ```

2. **Render will automatically deploy** with the new email configuration

3. **Check the logs** in Render dashboard to ensure email is working

### **Step 4: Test Production Email**

1. **Go to your production URL** (e.g., `https://your-app.onrender.com`)
2. **Register a new user account**
3. **Check the user's email** for verification link
4. **Click the verification link** to verify the account

### **Production Email Features**

✅ **Real emails sent to customers**  
✅ **Professional email templates**  
✅ **Secure verification tokens**  
✅ **24-hour token expiration**  
✅ **Automatic cleanup of expired tokens**  

### **Monitoring Production**

**Check Render Logs for:**
- ✅ Email sent successfully
- ❌ Email sending errors
- 📧 Verification link generation

**Expected Log Messages:**
```
✅ Email configuration loaded successfully.
✅ Email sent successfully to customer@example.com
```

### **Troubleshooting Production**

**If emails aren't sending:**
1. Check Gmail credentials in Render environment variables
2. Verify 2-Factor Authentication is enabled
3. Ensure App Password is correct
4. Check Render logs for specific error messages

**If verification links don't work:**
1. Check that `FLASK_ENV=production` is set
2. Verify the production URL is correct
3. Check that HTTPS is working properly

### **Alternative Email Services**

For higher volume or better deliverability, consider:

**SendGrid (Recommended for production):**
```
SENDGRID_API_KEY=your-api-key
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
```

**Mailgun:**
```
MAILGUN_API_KEY=your-api-key
MAIL_SERVER=smtp.mailgun.org
MAIL_PORT=587
MAIL_USERNAME=your-mailgun-username
MAIL_PASSWORD=your-mailgun-password
```

### **Ready for Customers!**

Once deployed with proper email configuration:
- ✅ Customers can register accounts
- ✅ Verification emails will be sent automatically
- ✅ Professional email templates
- ✅ Secure verification process
- ✅ Works on your production domain

Your customer-facing application will have full email verification functionality! 🎉 