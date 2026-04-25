# Send to Google Drive - Setup Guide

Calibre-Web can send ebooks directly to your personal Google Drive. This requires a one-time admin setup and a per-user connection step.

## Admin Setup

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Create a new project (or select an existing one)
3. Enable the **Google Drive API**:
   - Navigate to **APIs & Services → Library**
   - Search for "Google Drive API" and click **Enable**
4. Create OAuth credentials:
   - Navigate to **APIs & Services → Credentials**
   - Click **Create Credentials → OAuth client ID**
   - Application type: **Web application**
   - Name: anything (e.g., "Calibre-Web")
   - Under **Authorized redirect URIs**, add:
     ```
     https://your-calibre-web-domain/gdrive_send/callback
     ```
   - Click **Create** and note the **Client ID** and **Client Secret**

### 2. Configure Calibre-Web

1. Log in as admin
2. Go to **Admin → Edit Google Drive Send Settings**
3. Enter the **Client ID** and **Client Secret** from step 1
4. Click **Save**

The admin settings page also displays the exact redirect URI to use in Google Cloud Console.

## User Setup

### Connecting Your Google Drive

1. Go to **Profile** (click your username → Profile)
2. Click **Connect Google Drive**
3. You'll be redirected to Google to authorize access
4. After approving, you'll be returned to your profile with a "Connected" status
5. Optionally change the **Google Drive Folder Name** (default: "Calibre-Web")

### Sending Books

1. Open any book's detail page
2. Click the **Send to Google Drive** button (cloud upload icon)
3. Choose the format you want to send
4. A success message confirms the upload is queued
5. The file will appear in your Google Drive in the configured folder

### Supported Formats

- **Direct send**: EPUB, PDF, AZW3, CBZ, CBR
- **Convert and send**: If a book only has MOBI or AZW3, an option to convert to EPUB and send will appear (requires Calibre ebook-convert to be configured)

### Disconnecting

1. Go to **Profile**
2. Click **Disconnect Google Drive**

## Troubleshooting

### "Google OAuth library not installed"
The `google-auth-oauthlib` Python package is missing. On Gentoo, enable the `gdrive-send` USE flag:
```
echo "www-apps/calibre-web gdrive-send" >> /etc/portage/package.use/calibre-web
emerge -v www-apps/calibre-web
```

### "Google Drive Send is not configured"
The admin hasn't set up OAuth credentials yet. See [Admin Setup](#admin-setup) above.

### "redirect_uri_mismatch" error from Google
The redirect URI in Google Cloud Console doesn't match what Calibre-Web generates. Check:
- The URI must be **exactly** `https://your-domain/gdrive_send/callback`
- It must use `https://`, not `http://`
- No trailing slash
- The domain must match how users access Calibre-Web

If Calibre-Web is behind a reverse proxy, ensure the proxy passes `X-Forwarded-Proto` and `X-Forwarded-Host` headers, and that Calibre-Web has `ProxyFix` middleware enabled.

### "Missing code verifier" error
This is handled automatically. If you see this error, ensure you're running the latest version of the code.

### "Google Drive API has not been used in project..."
The Google Drive API isn't enabled in your Google Cloud project. Go to **APIs & Services → Library** in Google Cloud Console, search for "Google Drive API", and enable it. Wait a few minutes for it to propagate.

### Book queued but nothing appears in Drive
Check the Calibre-Web log for errors:
```
tail -50 /var/lib/calibre-web/calibre-web.log | grep -i gdrive
```
Common causes:
- Google Drive API not enabled (see above)
- OAuth token expired — disconnect and reconnect from your profile
- File permissions — ensure the Calibre library is readable by the calibre-web service user

### Reverse Proxy Configuration (Apache)

If Calibre-Web runs behind Apache, the SSL vhost needs to forward the original protocol and host:

```apache
<VirtualHost *:443>
    ServerName          books.example.com
    RequestHeader set   X-Forwarded-Proto "https"
    ProxyPreserveHost   On
    ProxyPass           / http://localhost:8083/
    ProxyPassReverse    / http://localhost:8083/
    SSLCertificateFile  /path/to/fullchain.pem
    SSLCertificateKeyFile /path/to/privkey.pem
</VirtualHost>
```

Calibre-Web uses Werkzeug's `ProxyFix` middleware to read these headers.
