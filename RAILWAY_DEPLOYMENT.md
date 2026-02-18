# Railway Deployment Guide for Calibre-Web

## Quick Deploy

1. **Create a new Railway project** or link to an existing one
2. **Deploy from GitHub** - Railway will automatically detect the configuration
3. **Add a Volume** (REQUIRED for persistent data):
   - Mount path: `/app/config`
   - This stores your settings database (`app.db`), user accounts, and encryption keys

## Configuration

### Environment Variables

The following environment variables are automatically configured:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | (set by Railway) | Server port - automatically used |
| `CALIBRE_DBPATH` | `/app/config` | Config directory path |
| `CACHE_DIRECTORY` | `/app/cache` | Cache directory for thumbnails |

### Optional Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Flask secret key (auto-generated if not set) |
| `FLASK_DEBUG` | Set to `1` for debug logging |

## Important Notes

### Persistent Storage

**You MUST attach a Railway Volume to `/app/config`** - Without this:
- All users and settings will be lost on each deploy
- You'll need to reconfigure the app every time

### Calibre Library

Calibre-Web needs access to a Calibre library (`metadata.db` + book files). Options:

1. **Google Drive Integration**: Configure via the web UI after first deploy
2. **Mount a volume**: Add another volume with your Calibre library
3. **External storage**: Use an S3-compatible storage with appropriate plugins

### First Login

After deployment:
- URL: `https://your-app.railway.app`
- Default username: `admin`
- Default password: `admin123`

**Change the admin password immediately after first login!**

## Build Configuration

The deployment uses:
- **Builder**: Nixpacks
- **Python**: 3.11
- **System packages**: ImageMagick, Ghostscript (for PDF/image processing)

## Troubleshooting

### App not starting
- Check logs with `railway logs`
- Ensure the volume is mounted at `/app/config`

### "Database is locked" errors
- This can happen if the app restarts mid-write
- Restart the service to clear the lock

### Missing covers/thumbnails
- Ensure `CACHE_DIRECTORY` volume is mounted
- Regenerate thumbnails via Admin > Scheduled Tasks

## File Structure

```
/app/
├── config/           # Mount volume here (REQUIRED)
│   ├── app.db       # Settings and users database
│   ├── gdrive.db    # Google Drive sync state
│   └── .key         # Encryption key
├── cache/           # Thumbnail cache
└── cps/             # Application code
```
