# Google Cloud TTS Setup Guide

## Implementation Complete ✅

The system now uses Google Cloud Text-to-Speech as the primary TTS provider with automatic fallback to browser TTS.

## Features
- **High-quality voices** for both English and Chinese
- **Automatic caching** to reduce API costs
- **Automatic fallback** to browser TTS if Google Cloud is unavailable
- **Better volume and quality** on iPhone devices

## Setup Instructions

### 1. Install Dependencies

Backend dependencies are already added to `requirements.txt`. Install them:

```bash
cd SpellBackend
pip install -r requirements.txt
```

### 2. Set Up Google Cloud Credentials

#### Option A: Using Service Account (Recommended for Production)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Cloud Text-to-Speech API:
   - Go to APIs & Services > Library
   - Search for "Cloud Text-to-Speech API"
   - Click Enable

4. Create a service account:
   - Go to IAM & Admin > Service Accounts
   - Click "Create Service Account"
   - Name it (e.g., "spell-tts")
   - Grant role: Search for "text-to-speech" and select **"Cloud Text-to-Speech Client"**
     - Alternative: Use **"Editor"** role for testing (simpler, works fine)
     - ⚠️ NOT "Speech-to-Text" - that's a different service!
   - Click "Create Key" → JSON
   - Download the JSON file

5. Set the environment variable:

**Linux/Mac:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"
```

**Windows PowerShell:**
```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\ZJB\archive\spell\gen-lang-client-0459022547-54fddcc160cd.json"
```

**For deployment (Fly.io):**

⚠️ **NEVER** commit the JSON file to your repository!

1. Set the credentials as a Fly.io secret (run from your local machine):
```bash
# From PowerShell
cd C:\ZJB\archive\spell\SpellBackend
fly secrets set GOOGLE_APPLICATION_CREDENTIALS_JSON="$(Get-Content C:\ZJB\archive\spell\gen-lang-client-0459022547-54fddcc160cd.json -Raw)"

# From Linux/Mac
fly secrets set GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat /path/to/your-service-account-key.json)"
```

2. The backend will automatically detect and use the secret (already configured in `tts_service.py`)

3. Deploy:
```bash
fly deploy
```

The TTS service will automatically create a temporary credentials file from the secret on startup.

#### Option B: Using Default Credentials (Development)

If you have gcloud CLI installed:
```bash
gcloud auth application-default login
```

### 3. Test the Backend

Start your backend server:
```bash
cd SpellBackend
python main.py
```

Test the TTS endpoint:
```bash
# Test English
curl "http://localhost:8000/api/tts/speak?text=hello&lang=en-US" -o test_en.mp3

# Test Chinese
curl "http://localhost:8000/api/tts/speak?text=你好&lang=zh-CN" -o test_zh.mp3

# Check status
curl "http://localhost:8000/api/tts/status"
```

### 4. Deploy to Production

If using Fly.io, update your `fly.toml` to mount the credentials:

```toml
[env]
  GOOGLE_APPLICATION_CREDENTIALS = "/app/credentials.json"
```

Then set the secret:
```bash
fly secrets set GOOGLE_APPLICATION_CREDENTIALS_JSON="$(cat your-key.json)"
```

### 5. No Changes Needed for Flutter

The Flutter web app is already updated to:
1. Try Google Cloud TTS first
2. Automatically fallback to browser TTS if unavailable

## Cost Estimation

Google Cloud TTS pricing (as of 2024):
- **Standard voices**: $4 per 1 million characters
- **WaveNet voices**: $16 per 1 million characters
- **Neural2 voices**: $16 per 1 million characters
- **First 4 million characters free per month**

With caching enabled (already implemented), repeated words cost nothing!

## Troubleshooting

### TTS not working in production

1. Check if credentials are set:
```bash
fly ssh console
echo $GOOGLE_APPLICATION_CREDENTIALS
```

2. Check logs:
```bash
fly logs
```

Look for "Google Cloud TTS initialized successfully" or error messages.

### Still using browser TTS

If the frontend still uses browser TTS, it means:
- Backend TTS service is not configured (check credentials)
- Backend is unreachable (check CORS and network)
- The app automatically falls back (this is expected behavior)

Check browser console for "Google TTS failed" messages.

## Voice Quality Settings

Default settings in `tts_service.py`:
- **Audio format**: MP3
- **Speaking rate**: 1.0 (normal)
- **Pitch**: 0.0 (normal)
- **Volume**: 0.0 dB (normal)

You can adjust these in the `synthesize_speech` method for different effects.

## Available Endpoints

- `GET /api/tts/speak?text=hello&lang=en-US` - Generate speech (short texts)
- `POST /api/tts/speak` - Generate speech (longer texts, JSON body)
- `GET /api/tts/voices?lang=en-US` - List available voices
- `GET /api/tts/status` - Check if service is enabled
- `GET /api/tts/stats` - View usage statistics (API calls, cache hits, cost estimate)

## Monitoring Usage

Check TTS usage statistics at any time:

```bash
# Local testing
curl http://localhost:8000/api/tts/stats

# Network testing (replace with your PC's IP)
curl http://172.20.10.13:8000/api/tts/stats

# Production
curl https://spellbackend.fly.dev/api/tts/stats
```

Or open in browser: `http://YOUR_SERVER/api/tts/stats`

Response includes:
- **api_calls**: Number of actual Google Cloud API calls (excludes cache)
- **cache_hits**: Times audio was served from cache
- **total_characters**: Total characters synthesized
- **estimated_cost_usd**: Estimated cost based on Google pricing

**Note**: Stats reset on server restart. For persistent tracking, use [Google Cloud Console](https://console.cloud.google.com/apis/api/texttospeech.googleapis.com/quotas).

## Testing

Test on iPhone Safari after deployment to verify improved quality and volume!
