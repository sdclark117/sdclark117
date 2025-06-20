# Gmail SMTP Setup Guide

This guide will help you configure Gmail SMTP for sending verification and password reset emails in your Business Lead Finder application.

## Prerequisites

- A Gmail account
- 2-Factor Authentication enabled on your Gmail account
- App Password generated for the application

## Step-by-Step Setup

### 1. Enable 2-Factor Authentication

1. Go to your Google Account settings: https://myaccount.google.com/
2. Navigate to "Security"
3. Under "Signing in to Google," click on "2-Step Verification"
4. Follow the prompts to enable 2-Factor Authentication

### 2. Generate an App Password

1. Go to your Google Account settings: https://myaccount.google.com/
2. Navigate to "Security"
3. Under "Signing in to Google," click on "App passwords"
4. Select "Mail" as the app and "Other" as the device
5. Enter a name for your app (e.g., "Business Lead Finder")
6. Click "Generate"
7. **Copy the 16-character password** that appears (you won't see it again!)

### 3. Set Environment Variables

Create a `.env` file in your project root directory (if it doesn't exist) and add the following variables:

```env
# Gmail Configuration
GMAIL_USERNAME=your.email@gmail.com
GMAIL_APP_PASSWORD=your-16-character-app-password

# Other existing variables
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
SECRET_KEY=your-secret-key-here
```

**Important Notes:**
- Replace `your.email@gmail.com` with your actual Gmail address
- Replace `your-16-character-app-password` with the app password you generated
- The app password is 16 characters long with no spaces
- Keep your `.env` file secure and never commit it to version control

### 4. Test the Configuration

1. Start your Flask application:
   ```bash
   python app.py
   ```

2. Register a new user account
3. Check your email for the verification link
4. Test the password reset functionality

## Troubleshooting

### Common Issues

#### 1. "Authentication failed" error
- **Cause**: Incorrect app password or username
- **Solution**: Double-check your GMAIL_USERNAME and GMAIL_APP_PASSWORD in the .env file

#### 2. "SMTP server connection failed" error
- **Cause**: Network issues or Gmail blocking the connection
- **Solution**: 
  - Check your internet connection
  - Ensure you're using the correct SMTP settings (smtp.gmail.com:587)
  - Try again later if Gmail is temporarily blocking connections

#### 3. "Less secure app access" error
- **Cause**: Using regular password instead of app password
- **Solution**: Generate and use an app password as described above

#### 4. Emails not being sent
- **Cause**: Environment variables not loaded properly
- **Solution**: 
  - Ensure your `.env` file is in the project root directory
  - Restart your Flask application after making changes
  - Check that the variable names match exactly

### Debug Mode

To see detailed email sending logs, run your application in debug mode:

```python
# In app.py, ensure debug is enabled
if __name__ == '__main__':
    app.run(debug=True)
```

### Alternative Email Services

If you prefer not to use Gmail, you can configure other email services:

#### SendGrid
```python
app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'apikey'
app.config['MAIL_PASSWORD'] = 'your-sendgrid-api-key'
```

#### Mailgun
```python
app.config['MAIL_SERVER'] = 'smtp.mailgun.org'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-mailgun-username'
app.config['MAIL_PASSWORD'] = 'your-mailgun-password'
```

## Security Best Practices

1. **Never commit your .env file** to version control
2. **Use app passwords** instead of your regular Gmail password
3. **Enable 2-Factor Authentication** on your Gmail account
4. **Regularly rotate** your app passwords
5. **Monitor** your Gmail account for any suspicious activity

## Production Deployment

For production deployment:

1. **Use environment variables** in your hosting platform (Heroku, Render, etc.)
2. **Set up proper logging** for email sending errors
3. **Monitor email delivery rates** and bounce rates
4. **Consider using a dedicated email service** like SendGrid or Mailgun for better deliverability

## Email Templates

The application sends two types of emails:

### 1. Email Verification
- **Subject**: "Verify Your Email - Business Lead Finder"
- **Content**: Welcome message with verification link
- **Expiry**: 24 hours

### 2. Password Reset
- **Subject**: "Password Reset - Business Lead Finder"
- **Content**: Password reset instructions with secure link
- **Expiry**: 1 hour

Both emails include:
- Professional HTML formatting
- Clear call-to-action buttons
- Security warnings
- Expiration information

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Verify your Gmail account settings
3. Test with a simple email sending script
4. Check your application logs for detailed error messages

For additional help, refer to:
- [Gmail SMTP Settings](https://support.google.com/mail/answer/7126229)
- [Google App Passwords](https://support.google.com/accounts/answer/185833)
- [Flask-Mail Documentation](https://pythonhosted.org/Flask-Mail/) 