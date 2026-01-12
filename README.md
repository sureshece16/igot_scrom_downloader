# iGOT SCORM Downloader

A web-based application to download SCORM files from the iGOT Karmayogi platform. This tool allows you to download multiple courses at once and packages them into a single ZIP file.

## Features

✨ **Modern Web Interface** - Clean, professional UI with Karmayogi Bharat branding
📦 **Batch Download** - Process multiple course DO IDs at once
🔄 **Automatic Retry** - 3 retry attempts with exponential backoff for network errors
📊 **Real-time Progress** - Live updates on download status and progress
🗂️ **Smart Naming** - Folders named with course/module names + DO IDs
📋 **Download Summary** - Copyable summary with statistics and errors
🗑️ **Auto Cleanup** - Automatic removal of old files and temporary folders
📥 **ZIP Packaging** - All downloads packaged into a single ZIP file

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/igot_scrom_downloader.git
   cd igot_scrom_downloader
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the application:**
   ```bash
   python app.py
   ```

2. **Access the web interface:**
   - Open your browser and navigate to: `http://localhost:5000/igot_scrom_downloader`

3. **Download SCORM files:**
   - Enter course DO IDs (one per line)
   - Click "Start Download"
   - Watch real-time progress
   - Download the ZIP file when complete
   - Copy the summary to share via email

## Project Structure

```
igot_scrom_downloader/
├── app.py                      # Flask web application
├── scorm_downloader.py         # Core SCORM downloader class
├── requirements.txt            # Python dependencies
├── templates/
│   └── index.html             # Web UI template
├── static/
│   ├── styles.css             # UI styling
│   └── script.js              # Client-side logic
├── email_config.py.example    # Email configuration template
└── WEB_UI_GUIDE.md           # Detailed user guide
```

## Configuration

### Email Notifications (Optional)

If you want to enable email notifications:

1. Copy `email_config.py.example` to `email_config.py`
2. Fill in your SMTP settings
3. Set `ENABLE_EMAIL = True`

**Note:** Email is optional. You can copy the summary from the UI instead.

## Folder Structure

Downloaded files are organized as:

```
CourseName(20chars)_DOID/
  ├── ModuleName(25chars)_DOID/
  │   └── ModuleName_DOID.zip
  └── AnotherModule_DOID/
      └── AnotherModule_DOID.zip
```

## Features in Detail

### Automatic Retry Logic
- Network errors trigger automatic retries (up to 3 attempts)
- Exponential backoff: 2s, 4s, 8s between retries
- Detailed logging of retry attempts

### Smart Cleanup
- Old ZIP files deleted before each download
- Temporary folders cleaned up after ZIP creation
- Only the latest ZIP file remains on the server

### Download Summary
- Courses processed
- SCORM files downloaded
- Failed downloads
- Error details
- Copyable text format for easy sharing

## Troubleshooting

### Port Already in Use
If you see "Address already in use", stop any running instances:
```bash
# Windows
Get-Process -Name python | Stop-Process -Force

# Linux/Mac
killall python
```

### Downloads Failing
- Check your internet connection
- Verify the DO IDs are correct
- Check the Activity Log for specific errors
- The app will automatically retry up to 3 times

### Path Too Long (Windows)
The app automatically shortens folder and file names to prevent Windows MAX_PATH issues.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Acknowledgments

- Built for the iGOT Karmayogi Bharat platform
- Uses Flask for the web interface
- Implements Server-Sent Events for real-time updates

## Support

For issues or questions, please open an issue on GitHub.

---

**© 2026 Karmayogi Bharat | iGOT Platform**
