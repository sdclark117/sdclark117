# Google Sheets API Setup Guide

To allow the application to export data to Google Sheets, you need to create a **service account** in the Google Cloud Platform (GCP) and authorize it to access the Google Sheets and Google Drive APIs.

Follow these steps to configure the API access:

## Step 1: Create a Google Cloud Platform (GCP) Project

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  If you don't have a project already, click the project dropdown in the top bar and click **"New Project"**.
3.  Give your project a name (e.g., "Business Leads Exporter") and click **"Create"**.

## Step 2: Enable the Google Sheets and Google Drive APIs

1.  In your GCP project, navigate to the **"APIs & Services" > "Library"** section from the left-hand menu.
2.  Search for **"Google Sheets API"** and click on it.
3.  Click the **"Enable"** button.
4.  Go back to the library, search for **"Google Drive API"**, and enable it as well. (The Drive API is needed to create and manage files).

## Step 3: Create a Service Account

1.  In the **"APIs & Services"** section, go to **"Credentials"**.
2.  Click **"Create Credentials"** and select **"Service account"**.
3.  Fill in the service account details:
    *   **Service account name**: Give it a descriptive name (e.g., "sheets-exporter-agent").
    *   **Service account ID**: This will be automatically generated.
    *   **Service account description**: (Optional) Add a description.
4.  Click **"Create and Continue"**.
5.  In the **"Grant this service account access to project"** step, select the role **"Project" > "Editor"** to give it sufficient permissions.
6.  Click **"Continue"**, then click **"Done"**.

## Step 4: Generate JSON Credentials

1.  On the **"Credentials"** page, you should see your newly created service account under the "Service Accounts" section.
2.  Click on the service account's email address to manage it.
3.  Go to the **"Keys"** tab.
4.  Click **"Add Key"** and select **"Create new key"**.
5.  Choose **"JSON"** as the key type and click **"Create"**.
6.  A JSON file containing your credentials will be automatically downloaded. **Keep this file secure and do not share it publicly.**

## Step 5: Set Up Environment Variable on Render

The content of the downloaded JSON file needs to be stored as an environment variable in your Render project.

1.  Open the downloaded JSON file in a text editor.
2.  Copy the **entire content** of the file.
3.  Go to your service on the [Render Dashboard](https://dashboard.render.com/).
4.  Click on the **"Environment"** tab.
5.  Click **"Add Environment Variable"**.
6.  Set the following:
    *   **Key**: `GOOGLE_CREDENTIALS_JSON`
    *   **Value**: Paste the entire content of the JSON file here.
7.  Click **"Save Changes"**. Render will trigger a new deployment with this environment variable.

## Step 6: Share a Google Drive Folder with the Service Account (Optional but Recommended)

To keep your exported sheets organized, you can create a folder in your Google Drive and share it with your service account.

1.  In your Google Drive, create a new folder (e.g., "Exported Business Leads").
2.  Click the **"Share"** button for that folder.
3.  In the sharing dialog, paste the **service account's email address** (you can find this in the "Details" tab of your service account in the GCP Console). It will look something like `sheets-exporter-agent@your-project-id.iam.gserviceaccount.com`.
4.  Give the service account **"Editor"** permissions for the folder.
5.  Click **"Share"**.
6.  Now, copy the **folder ID** from the URL in your browser. It's the long string of characters after `https://.../folders/`.
7.  Add another environment variable in Render:
    *   **Key**: `GOOGLE_DRIVE_FOLDER_ID`
    *   **Value**: Paste the folder ID here.

By doing this, all exported sheets will be automatically saved in this specific folder in your Google Drive. If you skip this step, the sheets will be created in the service account's own "My Drive" folder, which is less convenient to access. 