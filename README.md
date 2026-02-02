# Spell Practice Backend
Run `main.py` with uvicorn to start the API.

Option1 (Better):
fly.io deployment steps:
1. install fly.io if needed: iwr https://fly.io/install.ps1 -useb | iex
2. flyctl auth signup   # or: fly auth login if haven't login
    #please sign in with github burnlm@hotmail.com (github account)
3. Set up Google Cloud TTS credentials (one-time setup):
   
   **Option A: Via Fly.io Dashboard (Easiest)**
   - Go to https://fly.io/dashboard
   - Select your app "spellbackend"
   - Click "Secrets" in the left menu
   - Click "Add Secret"
   - Name: `GOOGLE_APPLICATION_CREDENTIALS_JSON`
   - Value: Open `C:\ZJB\archive\spell\gen-lang-client-0459022547-54fddcc160cd.json` in Notepad, copy ALL content, paste it
   - Click "Set Secret"
   
   **Option B: Via Command Line (Advanced)**
   ```powershell
   cd C:\ZJB\archive\spell\SpellBackend
   # Create temporary file with JSON content
   Get-Content C:\ZJB\archive\spell\gen-lang-client-0459022547-54fddcc160cd.json -Raw | Set-Content temp_creds.txt -NoNewline
   # Set secret
   flyctl secrets set "GOOGLE_APPLICATION_CREDENTIALS_JSON=$(Get-Content temp_creds.txt -Raw)"
   # Clean up
   Remove-Item temp_creds.txt
   ```

4. flyctl deploy --local-only #if docker is installed and running.

5. Verify TTS is working after deployment:
   ```bash
   curl https://spellbackend.fly.dev/api/tts/status
   # Should return: {"enabled":true,"service":"Google Cloud Text-to-Speech"}
   ``` 


option2:
render.com
simply connect to the github. Automatically deployment.
Cons: it will stop clean the database for free version.

## Database Backup to Google Drive

### Setup Steps:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable **Google Drive API**
3. Go to **Credentials** → **Create Credentials** → **Service Account**
4. Download the JSON key file
5. Create a folder in Google Drive
6. Share the folder with the service account email (e.g., `backup@project.iam.gserviceaccount.com`)
7. Get the folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

### Set Environment Variables on fly.io:
```bash
# Encode the JSON credentials to base64
$content = Get-Content -Raw service-account.json
$bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
$base64 = [Convert]::ToBase64String($bytes)

# Set the secrets on fly.io
flyctl secrets set GOOGLE_DRIVE_CREDENTIALS="$base64"
flyctl secrets set GOOGLE_DRIVE_FOLDER_ID="your-folder-id-here"
```

### Manual Backup:
```bash
# Via API endpoint
curl -X POST https://spell-backend.fly.dev/admin/backup

# Or run locally
python backup_to_drive.py
```

### Automatic Daily Backup:
Option A: Use fly.io scheduled machines (see fly.toml)
Option B: Use external cron service (e.g., cron-job.org) to call POST /admin/backup daily