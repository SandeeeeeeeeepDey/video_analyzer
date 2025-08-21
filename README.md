# Google Drive Integration Setup

This document outlines the steps to set up Google Drive integration for the McD Video Understanding application.

## User Provided Information

*   **Folder Name:** `drive in gradio` (to be created inside a `delete` folder)
*   **Email Address:** `1999sandeepdey@gmail.com`
*   **Project Name:** `dridiogoogledriveingradio`
*   **Service Account Name:** `googledriveingradio`

## Setup Steps

**Step 1: Create a Google Cloud Project**

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Click the project selector dropdown in the top bar, then click **"New Project"**.
3.  For **"Project name"**, enter `dridiogoogledriveingradio`.
4.  Click **"Create"**.

**Step 2: Enable the Google Drive API**

1.  Make sure your new project (`dridiogoogledriveingradio`) is selected in the project selector.
2.  In the navigation menu (the "hamburger" icon ☰), go to **"APIs & Services" > "Library"**.
3.  Search for "Google Drive API" and select it from the results.
4.  Click the **"Enable"** button.

**Step 3: Create a Service Account**

1.  In the navigation menu, go to **"IAM & Admin" > "Service Accounts"**.
2.  Click **"+ CREATE SERVICE ACCOUNT"**.
3.  For **"Service account name"**, enter `googledriveingradio`.
4.  Click **"CREATE AND CONTINUE"**.
5.  For the **"Role"**, select **"Project" > "Editor"**.
6.  Click **"CONTINUE"**, then click **"DONE"**.

**Step 4: Get Your Service Account Credentials**

1.  You should now see the `googledriveingradio` service account in the list. Click the three dots under the **"Actions"** column and select **"Manage keys"**.
2.  Click **"ADD KEY" > "Create new key"**.
3.  Choose **"JSON"** as the key type and click **"CREATE"**. A JSON file will be downloaded to your computer.

**Step 5: Save the Credentials File**

1.  Rename the downloaded JSON file to `google_drive_credentials.json`.
2.  Move this file into the root of your project directory: `C:\Users\xelpmoc\Documents\projects_001\McD_VideoUnderstanding\`.

**Step 6: Share Your Google Drive Folder**

1.  Open your Google Drive.
2.  Create a new folder named `delete`.
3.  Inside the `delete` folder, create another folder named `drive in gradio`.
4.  Right-click the `drive in gradio` folder and select **"Share"**.
5.  In the "Add people and groups" field, paste the email address of the service account you created. You can find this email in the details of the service account in the Google Cloud Console (it will look something like `googledriveingradio@dridiogoogledriveingradio.iam.gserviceaccount.com`).
6.  Click **"Send"**.
