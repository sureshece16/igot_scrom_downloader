# 🌐 iGOT SCORM Downloader - Web UI Guide

## 📋 Overview

This web application provides a simple, user-friendly interface to download SCORM files from iGOT Karmayogi courses. Simply enter multiple DO IDs, and the application will download all SCORM files and package them into a single ZIP file.

## ✨ Features

- **Simple Input**: Enter multiple DO IDs (one per line)
- **Real-time Progress**: Watch downloads progress in real-time
- **Beautiful UI**: Modern, premium dark mode design with Karmayogi Bharat aesthetics
- **Automatic Packaging**: All downloads automatically packaged into one ZIP file
- **Easy Sharing**: Share with anyone who has Python installed

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- Internet connection

### Installation

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python app.py
   ```

3. **Access the Web UI**
   - Open your browser and navigate to: `http://localhost:5000/igot_scrom_downloader`

## 📖 How to Use

### Step 1: Enter DO IDs

1. In the text area, enter the DO IDs you want to download (one per line)
2. Example:
   ```
   do_113768226086068224132
   do_113768226086068224133
   do_113768226086068224134
   ```

### Step 2: Start Download

1. Click the **"Start Download"** button
2. The application will begin processing your courses
3. You'll see real-time progress updates including:
   - Total courses
   - Courses completed
   - SCORM files downloaded
   - Progress bar
   - Activity log

### Step 3: Download ZIP File

1. Once all downloads are complete, a success message will appear
2. Click the **"Download ZIP File"** button
3. Your browser will download a ZIP file containing all SCORM files
4. The ZIP file will be named: `scorm_downloads_YYYYMMDD_HHMMSS.zip`

### Step 4: Start New Download (Optional)

- Click **"Start New Download"** to process more DO IDs

## 🎨 Interface Features

### Input Section
- Large text area for entering multiple DO IDs
- Clear button to reset input
- Start button to begin download process

### Progress Section
- **Statistics Cards**: Show total courses, completed count, and SCORM files downloaded
- **Progress Bar**: Visual indicator of overall progress with animated gradient
- **Current Activity**: Shows what the application is currently doing
- **Activity Log**: Detailed log of all operations

### Download Section
- **Success Message**: Confirmation of completion
- **Statistics Summary**: Final count of courses and SCORM files
- **Download Button**: Downloads the final ZIP file
- **Start New Button**: Begins a new download session

## 🔧 Technical Details

### Architecture

- **Backend**: Flask web server (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Real-time Updates**: Server-Sent Events (SSE)
- **File Processing**: Integrates with existing `scorm_downloader.py`

### API Endpoints

- `GET /igot_scrom_downloader`: Main UI
- `POST /igot_scrom_downloader/api/download`: Start download process
- `GET /igot_scrom_downloader/api/progress`: Server-Sent Events for progress
- `GET /igot_scrom_downloader/api/download-zip`: Download final ZIP file
- `GET /igot_scrom_downloader/api/status`: Get current download status

### File Structure

```
igot_scrom_downloader/
├── app.py                      # Flask web server
├── scorm_downloader.py         # Core downloader logic
├── templates/
│   └── index.html              # Main UI template
├── static/
│   ├── styles.css              # Styling
│   └── script.js               # Client-side logic
├── requirements.txt            # Python dependencies
└── WEB_UI_GUIDE.md            # This file
```

## 📤 Sharing with Others

To share this application with colleagues:

1. **Share the entire project folder** containing all files
2. **Provide these instructions**:
   ```bash
   # Install dependencies
   pip install -r requirements.txt
   
   # Run the application
   python app.py
   
   # Open browser to
   http://localhost:5000/igot_scrom_downloader
   ```

3. **Requirements**:
   - Python 3.7+
   - Internet connection
   - Web browser

## ⚙️ Configuration

### Change Port Number

By default, the app runs on port 5000. To change this:

1. Open `app.py`
2. Modify the last line:
   ```python
   app.run(debug=True, threaded=True, port=8080)  # Change port here
   ```

### Change Download Folder

Downloads are stored in temporary folders and cleaned up after ZIP creation. To keep the raw downloads:

1. Open `app.py`
2. Comment out the cleanup section in the `download_worker` function:
   ```python
   # Clean up the session folder
   # if os.path.exists(session_folder):
   #     shutil.rmtree(session_folder)
   ```

## 🐛 Troubleshooting

### Port Already in Use

If you see "Address already in use" error:

1. Change the port in `app.py` (see Configuration above)
2. Or stop the application using that port

### No Progress Updates

If progress updates don't appear:

1. Check browser console for errors (F12)
2. Ensure Server-Sent Events are supported (all modern browsers)
3. Try refreshing the page

### Download Failed

If download fails:

1. Check the activity log for error messages
2. Verify DO IDs are correct
3. Check internet connection
4. Try downloading one course at a time to identify problematic IDs

### ZIP File Empty

If the ZIP file is empty:

1. Check if DO IDs are valid
2. Verify courses contain SCORM content (mimeType: application/vnd.ekstep.html-archive)
3. Check the activity log for download errors

## 📊 Performance Tips

- **Small Batches**: For large numbers of courses, split into smaller batches (10-20 at a time)
- **Stable Connection**: Ensure stable internet connection during downloads
- **Disk Space**: Ensure sufficient disk space (estimate 1-2 GB for 75 courses)

## 🔒 Security & Privacy

- ✅ No credentials required (public content)
- ✅ All data processed locally
- ✅ No external tracking or analytics
- ✅ Downloads from official iGOT domains only

## 📝 Notes

- **SCORM Only**: Only downloads SCORM resources (mimeType: application/vnd.ekstep.html-archive)
- **Auto-Cleanup**: Temporary folders are automatically deleted after ZIP creation
- **Session-Based**: Each download creates a unique session with timestamped output
- **Browser-Based**: Keep the browser tab open during downloads for real-time updates

## 💡 Advanced Usage

### Using from Command Line (Original Method)

The original command-line interface is still available:

1. Edit `course_ids.py` to add DO IDs
2. Run: `python scorm_downloader.py`

### Automation

To automate downloads:

1. Use the API endpoints directly with tools like `curl` or `requests`
2. Example with curl:
   ```bash
   curl -X POST http://localhost:5000/igot_scrom_downloader/api/download \
        -H "Content-Type: application/json" \
        -d '{"do_ids": ["do_123", "do_456"]}'
   ```

## 🎉 Enjoy!

You now have a simple, shareable tool for downloading SCORM files from iGOT Karmayogi courses. The web interface makes it accessible to anyone, even those not familiar with command-line tools.

---

**Version**: 1.0  
**Created**: January 2026  
**For**: iGOT Karmayogi Project
