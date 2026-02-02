"""
Google Drive Backup Script for SQLite Database
Backs up the database to Google Drive daily

Setup:
1. Create a Google Cloud Service Account
2. Enable Google Drive API
3. Download the JSON credentials file
4. Share a Google Drive folder with the service account email
5. Set environment variables:
   - GOOGLE_DRIVE_CREDENTIALS: Base64 encoded JSON credentials OR path to JSON file
   - GOOGLE_DRIVE_FOLDER_ID: The ID of the shared Google Drive folder
"""

import os
import shutil
import base64
import json
from datetime import datetime
from pathlib import Path

# Check if google libraries are available
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False
    print("Google libraries not installed. Run: pip install google-api-python-client google-auth")


DATABASE_PATH = Path(__file__).parent / "database" / "db.sqlite3"
BACKUP_DIR = Path(__file__).parent / "backups"
SCOPES = ['https://www.googleapis.com/auth/drive.file']


def get_credentials():
    """Get Google credentials from environment variable."""
    creds_env = os.getenv('GOOGLE_DRIVE_CREDENTIALS')
    
    if not creds_env:
        raise ValueError("GOOGLE_DRIVE_CREDENTIALS environment variable not set")
    
    # Check if it's a file path or base64 encoded JSON
    if os.path.exists(creds_env):
        return service_account.Credentials.from_service_account_file(creds_env, scopes=SCOPES)
    else:
        # Assume it's base64 encoded JSON
        try:
            creds_json = base64.b64decode(creds_env).decode('utf-8')
            creds_dict = json.loads(creds_json)
            return service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        except Exception as e:
            raise ValueError(f"Failed to parse credentials: {e}")


def create_local_backup():
    """Create a local backup of the database with timestamp."""
    if not DATABASE_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DATABASE_PATH}")
    
    BACKUP_DIR.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"db_backup_{timestamp}.sqlite3"
    backup_path = BACKUP_DIR / backup_filename
    
    shutil.copy2(DATABASE_PATH, backup_path)
    print(f"Local backup created: {backup_path}")
    
    return backup_path, backup_filename


def upload_to_google_drive(file_path: Path, filename: str):
    """Upload a file to Google Drive."""
    if not GOOGLE_LIBS_AVAILABLE:
        raise ImportError("Google libraries not available")
    
    folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    if not folder_id:
        raise ValueError("GOOGLE_DRIVE_FOLDER_ID environment variable not set")
    
    credentials = get_credentials()
    service = build('drive', 'v3', credentials=credentials)
    
    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(str(file_path), mimetype='application/x-sqlite3')
    
    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, name, webViewLink'
    ).execute()
    
    print(f"Uploaded to Google Drive: {file.get('name')} (ID: {file.get('id')})")
    return file


def cleanup_old_backups(keep_local: int = 7, keep_drive: int = 30):
    """Remove old local backups, keeping the most recent ones."""
    if not BACKUP_DIR.exists():
        return
    
    backups = sorted(BACKUP_DIR.glob("db_backup_*.sqlite3"), reverse=True)
    
    for old_backup in backups[keep_local:]:
        old_backup.unlink()
        print(f"Deleted old local backup: {old_backup.name}")


def backup_database():
    """Main backup function - creates local backup and uploads to Google Drive."""
    print(f"Starting backup at {datetime.now().isoformat()}")
    
    try:
        # Create local backup
        backup_path, backup_filename = create_local_backup()
        
        # Upload to Google Drive if configured
        if os.getenv('GOOGLE_DRIVE_CREDENTIALS') and os.getenv('GOOGLE_DRIVE_FOLDER_ID'):
            if GOOGLE_LIBS_AVAILABLE:
                upload_to_google_drive(backup_path, backup_filename)
            else:
                print("Skipping Google Drive upload - libraries not installed")
        else:
            print("Skipping Google Drive upload - credentials not configured")
        
        # Cleanup old local backups
        cleanup_old_backups()
        
        print("Backup completed successfully!")
        return True
        
    except Exception as e:
        print(f"Backup failed: {e}")
        return False


if __name__ == "__main__":
    backup_database()
