# Deploying the Business Lead Finder Web Application

This guide will help you deploy the Business Lead Finder web application to PythonAnywhere.

## Step 1: Sign Up for PythonAnywhere

1. Go to [PythonAnywhere](https://www.pythonanywhere.com/)
2. Click "Pricing & Signup"
3. Choose the "Beginner" plan (it's free)
4. Create an account

## Step 2: Upload Your Code

1. Log in to your PythonAnywhere dashboard
2. Go to the "Files" tab
3. Create a new directory called `sneaker-agent`
4. Upload all your project files to this directory:
   - app.py
   - wsgi_config.py
   - requirements.txt
   - templates/index.html
   - Any other project files

## Step 3: Set Up a Virtual Environment

1. Go to the "Consoles" tab
2. Start a new Bash console
3. Run these commands:
   ```bash
   cd sneaker-agent
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

## Step 4: Configure the Web App

1. Go to the "Web" tab
2. Click "Add a new web app"
3. Choose "Manual configuration"
4. Select Python 3.10 (or the latest version)
5. In the "Code" section:
   - Set the source code directory to `/home/yourusername/sneaker-agent`
   - Set the working directory to `/home/yourusername/sneaker-agent`
   - Set the WSGI configuration file to `/var/www/yourusername_pythonanywhere_com_wsgi.py`

6. Edit the WSGI file:
   - Click on the WSGI configuration file link
   - Replace the contents with the contents of your `wsgi_config.py`
   - Update the path to match your username

## Step 5: Configure Static Files

1. In the "Static Files" section:
   - Add a new entry:
     - URL: `/static/`
     - Directory: `/home/yourusername/sneaker-agent/static`

## Step 6: Set Up Environment Variables

1. In the "Web" tab, go to the "Environment variables" section
2. Add your Google Maps API key:
   - Name: `GOOGLE_MAPS_API_KEY`
   - Value: Your API key

## Step 7: Reload the Web App

1. Click the "Reload" button in the "Web" tab
2. Your app should now be running at `yourusername.pythonanywhere.com`

## Troubleshooting

If you encounter any issues:

1. Check the error logs in the "Web" tab
2. Make sure all files are uploaded correctly
3. Verify that the virtual environment is activated
4. Ensure all dependencies are installed
5. Check that the WSGI configuration file is correct

## Security Considerations

1. Keep your Google Maps API key secure
2. Enable API key restrictions in the Google Cloud Console
3. Set up proper CORS policies if needed
4. Consider adding rate limiting for the API endpoints

## Maintenance

1. Regularly update your dependencies
2. Monitor your application logs
3. Keep your Google Maps API key active
4. Back up your data regularly

## Support

If you need help:
1. Check the PythonAnywhere documentation
2. Visit the PythonAnywhere forums
3. Contact PythonAnywhere support 