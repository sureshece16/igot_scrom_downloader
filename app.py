from flask import Flask, render_template, request, jsonify, send_file, Response, redirect, url_for, session, flash
from scorm_downloader import SCORMDownloader
import os
import json
import threading
import queue
import zipfile
from datetime import datetime, timedelta
import shutil
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from functools import wraps
import secrets

# Try to import email config
try:
    from email_config import (SMTP_SERVER, SMTP_PORT, SENDER_EMAIL, 
                              SENDER_PASSWORD, RECIPIENT_EMAIL, ENABLE_EMAIL)
except ImportError:
    ENABLE_EMAIL = False
    print("⚠️  email_config.py not found. Email notifications disabled.")

app = Flask(__name__, static_url_path='/igot_scrom_downloader/static')

# Configure for subdirectory deployment
app.config['APPLICATION_ROOT'] = '/igot_scrom_downloader'

# Session configuration
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_PATH'] = '/igot_scrom_downloader'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)  # 1 year, essentially no timeout
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Prevent JavaScript access to session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection

# Login API configuration
LOGIN_API_URL = 'https://portal.dev.karmayogibharat.net/cbp-tpc-ai/api/v1/auth/login'

# Global variables for progress tracking
progress_queue = queue.Queue()
download_status = {
    'is_running': False,
    'current_course': '',
    'courses_completed': 0,
    'total_courses': 0,
    'scorm_files_downloaded': 0,
    'errors': [],
    'download_complete': False,
    'zip_file_path': None
}

def login_required(f):
    """Decorator to protect routes that require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def log_callback(message):
    """Callback function to receive logs from SCORMDownloader"""
    progress_queue.put(message)
    print(message)  # Also print to console

def send_email_summary(stats, zip_filename):
    """Send email summary after download completion"""
    if not ENABLE_EMAIL:
        print("📧 Email notifications disabled")
        return
    
    try:
        # Create email content
        subject = f"✅ SCORM Download Complete - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Build HTML email body
        html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background: linear-gradient(135deg, #1e3a8a 0%, #f97316 100%); 
                   color: white; padding: 20px; border-radius: 10px; }}
        .stats {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .stat-item {{ display: flex; justify-content: space-between; padding: 8px 0; 
                      border-bottom: 1px solid #dee2e6; }}
        .stat-label {{ font-weight: bold; }}
        .stat-value {{ color: #f97316; }}
        .success {{ color: #22c55e; }}
        .error {{ color: #ef4444; }}
        .errors-section {{ background: #fff3cd; padding: 15px; border-radius: 8px; 
                          border-left: 4px solid #ffc107; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>📦 iGOT SCORM Download Summary</h2>
        <p>Download completed on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
    </div>
    
    <div class="stats">
        <h3>📊 Download Statistics</h3>
        <div class="stat-item">
            <span class="stat-label">Total Courses Processed:</span>
            <span class="stat-value">{stats['processed_courses']}/{stats['total_courses']}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">SCORM Files Found:</span>
            <span class="stat-value">{stats['total_scorm_files']}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Successfully Downloaded:</span>
            <span class="stat-value success">{stats['downloaded_files']}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">Failed Downloads:</span>
            <span class="stat-value error">{stats['failed_downloads']}</span>
        </div>
        <div class="stat-item">
            <span class="stat-label">ZIP File Created:</span>
            <span class="stat-value">{zip_filename}</span>
        </div>
    </div>
    
    {"<div class='errors-section'><h3>⚠️ Errors Encountered</h3><ul>" + 
     "".join([f"<li>{error}</li>" for error in stats['errors'][:10]]) + 
     "</ul></div>" if stats['errors'] else ""}
    
    <p style="margin-top: 30px; color: #6c757d; font-size: 0.9em;">
        This is an automated email from iGOT SCORM Downloader.<br>
        Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    </p>
</body>
</html>
"""
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        
        # Attach HTML content
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Send email
        print(f"📧 Sending email to {RECIPIENT_EMAIL}...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        
        print("✅ Email sent successfully!")
        progress_queue.put(f"📧 Email summary sent to {RECIPIENT_EMAIL}")
        
    except Exception as e:
        error_msg = f"❌ Failed to send email: {str(e)}"
        print(error_msg)
        progress_queue.put(error_msg)


def download_worker(do_ids):
    """Background worker to download SCORM files"""
    global download_status
    
    try:
        # Clean up old ZIP files and temporary folders before starting
        progress_queue.put("🗑️  Cleaning up old files...")
        
        # Delete old ZIP files
        old_zips = [f for f in os.listdir(os.getcwd()) if f.startswith('scorm_downloads_') and f.endswith('.zip')]
        for zip_file in old_zips:
            try:
                zip_path = os.path.join(os.getcwd(), zip_file)
                os.remove(zip_path)
                progress_queue.put(f"   ✅ Deleted old ZIP: {zip_file}")
            except Exception as e:
                progress_queue.put(f"   ⚠️  Could not delete {zip_file}: {e}")
        
        # Delete old temporary folders
        old_folders = [f for f in os.listdir(os.getcwd()) 
                      if os.path.isdir(f) and f.startswith('downloaded_courses_web_')]
        for folder in old_folders:
            try:
                folder_path = os.path.join(os.getcwd(), folder)
                shutil.rmtree(folder_path)
                progress_queue.put(f"   ✅ Deleted old folder: {folder}")
            except Exception as e:
                progress_queue.put(f"   ⚠️  Could not delete {folder}: {e}")
        
        if old_zips or old_folders:
            progress_queue.put(f"✅ Cleanup complete: {len(old_zips)} ZIP(s), {len(old_folders)} folder(s) removed")
        else:
            progress_queue.put("✅ No old files to clean up")
        
        download_status['is_running'] = True
        download_status['download_complete'] = False
        download_status['courses_completed'] = 0
        download_status['total_courses'] = len(do_ids)
        download_status['scorm_files_downloaded'] = 0
        download_status['errors'] = []
        
        # Create a unique session folder
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_folder = f"downloaded_courses_web_{session_id}"
        
        # Initialize downloader with custom folder
        downloader = SCORMDownloader(log_callback=log_callback)
        downloader.download_folder = session_folder
        
        progress_queue.put(f"📦 Starting download of {len(do_ids)} courses...")
        
        # Process courses
        downloader.process_multiple_courses(do_ids)
        
        # Update statistics
        download_status['courses_completed'] = downloader.stats['processed_courses']
        download_status['scorm_files_downloaded'] = downloader.stats['downloaded_files']
        download_status['errors'] = downloader.stats['errors']
        
        # Create ZIP file of all downloads
        zip_filename = f"scorm_downloads_{session_id}.zip"
        zip_path = os.path.join(os.getcwd(), zip_filename)
        
        progress_queue.put("📦 Creating ZIP file of all downloads...")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(session_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.getcwd())
                    zipf.write(file_path, arcname)
        
        download_status['zip_file_path'] = zip_path
        download_status['zip_filename'] = zip_filename
        download_status['download_complete'] = True
        
        progress_queue.put(f"✅ Download complete! ZIP file created: {zip_filename}")
        progress_queue.put(f"📊 Total SCORM files downloaded: {download_status['scorm_files_downloaded']}")
        progress_queue.put(f"💡 Check the summary below - you can copy and share it!")
        
        # Clean up the session folder
        progress_queue.put(f"🗑️  Cleaning up temporary folder: {session_folder}...")
        try:
            if os.path.exists(session_folder):
                shutil.rmtree(session_folder)
                progress_queue.put(f"✅ Temporary folder deleted successfully")
            else:
                progress_queue.put(f"⚠️  Temporary folder not found: {session_folder}")
        except Exception as cleanup_error:
            error_msg = f"⚠️  Could not delete temporary folder: {str(cleanup_error)}"
            progress_queue.put(error_msg)
            print(f"Cleanup error: {cleanup_error}")
            
    except Exception as e:
        import traceback
        import sys
        
        # Get full traceback
        tb_str = traceback.format_exc()
        
        error_msg = f"❌ Error during download: {type(e).__name__}: {str(e)}"
        progress_queue.put(error_msg)
        progress_queue.put(f"📋 Traceback:")
        
        # Split traceback into lines and send each
        for line in tb_str.split('\n'):
            if line.strip():
                progress_queue.put(f"  {line}")
                print(line, file=sys.stderr)
        
        download_status['errors'].append(error_msg)
        download_status['errors'].append(tb_str)
    finally:
        download_status['is_running'] = False


@app.route('/')
def root():
    """Redirect root to main application"""
    return redirect('/igot_scrom_downloader')

@app.route('/igot_scrom_downloader/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    # If already logged in, redirect to main app
    if 'user' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        if not username or not password:
            flash('Please enter both username and password', 'error')
            return render_template('login.html')
        
        try:
            # Call login API
            response = requests.post(
                LOGIN_API_URL,
                data={'username': username, 'password': password},
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=10
            )
            
            if response.status_code == 200:
                # Store user in session
                session.permanent = remember  # Only make permanent if remember me is checked
                session['user'] = username
                session['authenticated'] = True
                session['login_time'] = datetime.now().isoformat()
                
                # Redirect to next page or index
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/igot_scrom_downloader'):
                    return redirect(next_page)
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password', 'error')
                
        except requests.exceptions.Timeout:
            flash('Login service timeout. Please try again.', 'error')
        except requests.exceptions.ConnectionError:
            flash('Cannot connect to authentication service', 'error')
        except Exception as e:
            flash('An error occurred during login', 'error')
            print(f"Login error: {e}")
    
    return render_template('login.html')

@app.route('/igot_scrom_downloader/logout')
def logout():
    """Handle user logout"""
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/igot_scrom_downloader')
@login_required
def index():
    """Serve the main UI"""
    return render_template('index.html')

@app.route('/igot_scrom_downloader/api/download', methods=['POST'])
def start_download():
    """Start the download process"""
    global download_status
    
    if download_status['is_running']:
        return jsonify({'error': 'Download already in progress'}), 400
    
    data = request.json
    do_ids = data.get('do_ids', [])
    
    if not do_ids:
        return jsonify({'error': 'No DO IDs provided'}), 400
    
    # Clean and validate DO IDs
    do_ids = [do_id.strip() for do_id in do_ids if do_id.strip()]
    
    if not do_ids:
        return jsonify({'error': 'No valid DO IDs provided'}), 400
    
    # Clear the progress queue
    while not progress_queue.empty():
        progress_queue.get()
    
    # Start download in background thread
    thread = threading.Thread(target=download_worker, args=(do_ids,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': f'Download started for {len(do_ids)} courses',
        'total_courses': len(do_ids)
    })

@app.route('/igot_scrom_downloader/api/progress')
def progress():
    """Server-Sent Events endpoint for progress updates"""
    def generate():
        while True:
            try:
                # Get message from queue with timeout
                message = progress_queue.get(timeout=1)
                
                # Send the message as SSE
                yield f"data: {json.dumps({'message': message, 'status': download_status})}\n\n"
                
            except queue.Empty:
                # Send heartbeat to keep connection alive
                if not download_status['is_running'] and download_status['download_complete']:
                    # Send final status and close
                    yield f"data: {json.dumps({'message': 'DONE', 'status': download_status})}\n\n"
                    break
                else:
                    # Just send current status
                    yield f"data: {json.dumps({'message': '', 'status': download_status})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/igot_scrom_downloader/api/download-zip')
def download_zip():
    """Download the final ZIP file"""
    if not download_status['zip_file_path'] or not os.path.exists(download_status['zip_file_path']):
        return jsonify({'error': 'ZIP file not available'}), 404
    
    return send_file(
        download_status['zip_file_path'],
        as_attachment=True,
        download_name=os.path.basename(download_status['zip_file_path'])
    )

@app.route('/igot_scrom_downloader/api/status')
def get_status():
    """Get current download status"""
    return jsonify(download_status)

if __name__ == '__main__':
    print("=" * 70)
    print("🚀 SCORM Downloader Web UI - PRODUCTION MODE")
    print("=" * 70)
    print(f"📍 Access the application at: http://localhost:5000/igot_scrom_downloader")
    print("=" * 70)
    print("⚠️  Auto-reload is DISABLED to prevent download interruptions")
    print("=" * 70)
    # Run without debug mode to prevent auto-reload
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
