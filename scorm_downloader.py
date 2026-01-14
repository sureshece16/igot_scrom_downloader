import requests
import os
import json
import time
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    print("⚠️  youtube-transcript-api not installed. YouTube transcript support disabled.")

class SCORMDownloader:
    def __init__(self, base_url="https://portal.igotkarmayogi.gov.in", log_callback=None, update_status_callback=None):
        self.base_url = base_url
        self.content_api = f"{base_url}/api/content/v1/read"
        self.download_folder = "downloaded_courses"
        self.log_callback = log_callback
        self.update_status_callback = update_status_callback
        
        # YouTube rate limit prevention
        self.youtube_request_delay = 5  # seconds between YouTube requests
        self.last_youtube_request = 0
        
        # Create main download folder
        Path(self.download_folder).mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.stats = {
            "total_courses": 0,
            "processed_courses": 0,
            "total_scorm_files": 0,
            "downloaded_files": 0,
            "failed_downloads": 0,
            "total_mp4_files": 0,
            "transcripts_fetched": 0,
            "transcript_errors": 0,
            "errors": []
        }
    
    def log(self, message, end='\n'):
        """Log message to console and callback"""
        print(message, end=end)
        if self.log_callback:
            # Clean up carriage returns for UI
            clean_msg = message.replace('\r', '').strip()
            if clean_msg:
                self.log_callback(clean_msg)

    def sanitize_filename(self, name):
        """Remove invalid characters from filename and keep it short"""
        # Remove or replace invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Remove extra spaces and parentheses to shorten
        name = re.sub(r'\s*\([^)]*\)\s*', '_', name)  # Replace (APAR) with _
        name = re.sub(r'\s+', '_', name)  # Replace spaces with _
        name = re.sub(r'_+', '_', name)   # Replace multiple _ with single _
        name = name.strip('_')            # Remove leading/trailing _
        # Limit length to 30 characters to avoid Windows path issues (MAX_PATH = 260)
        if len(name) > 30:
            return name[:27] + "..."
        return name
    
    def convert_storage_url(self, url):
        """Convert Google Storage URL to iGOT content store URL"""
        if "storage.googleapis.com/igotprod" in url:
            return url.replace("https://storage.googleapis.com/igotprod", 
                             "https://igotkarmayogi.gov.in/content-store")
        return url
    
    def get_content_details(self, do_id):
        """Fetch content details using DO ID"""
        try:
            url = f"{self.content_api}/{do_id}"
            self.log(f"📡 Fetching content: {do_id}")
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("responseCode") == "OK":
                return data.get("result", {}).get("content", {})
            else:
                self.log(f"❌ API Error: {data.get('params', {}).get('errmsg', 'Unknown error')}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.log(f"❌ Network Error: {str(e)}")
            self.stats["errors"].append(f"Network error for {do_id}: {str(e)}")
            return None
        except Exception as e:
            self.log(f"❌ Error: {str(e)}")
            self.stats["errors"].append(f"Error for {do_id}: {str(e)}")
            return None
    
    def download_file_with_retry(self, url, filepath, max_retries=3):
        """Download file with retry logic for network errors"""
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    wait_time = 2 ** (attempt - 1)  # Exponential backoff: 2, 4, 8 seconds
                    self.log(f"     ⏱️  Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    self.log(f"     🔄 Retry attempt {attempt}/{max_retries}")
                
                success = self.download_file(url, filepath)
                if success:
                    return True
                    
                # If download_file returned False (not an exception), don't retry
                if attempt < max_retries:
                    self.log(f"     ⚠️  Download returned False, will retry...")
                    
            except Exception as e:
                if attempt < max_retries:
                    self.log(f"     ⚠️  Attempt {attempt} failed: {str(e)}")
                    self.log(f"     🔄 Will retry...")
                else:
                    self.log(f"     ❌ All {max_retries} attempts failed")
                    return False
        
        return False
    
    def download_file(self, url, filepath):
        """Download file from URL"""
        try:
            # Normalize the filepath
            filepath = os.path.normpath(filepath)
            self.log(f"⬇️  Downloading: {os.path.basename(filepath)}")
            self.log(f"     📂 Full path: {filepath}")
            self.log(f"     📏 Path length: {len(filepath)} chars")
            
            # Ensure parent directory exists
            parent_dir = os.path.dirname(filepath)
            
            # Try to create the directory
            try:
                Path(parent_dir).mkdir(parents=True, exist_ok=True)
                self.log(f"     ✅ Directory created/verified")
            except Exception as mkdir_error:
                self.log(f"     ❌ mkdir failed: {str(mkdir_error)}")
                self.log(f"     ❌ Error type: {type(mkdir_error).__name__}")
                return False
            
            self.log(f"     ⬇️  Fetching from server...")
            response = requests.get(url, stream=True, timeout=300)  # 5 minute timeout for large files
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            self.log(f"     📦 File size: {total_size / (1024*1024):.2f} MB")
            
            # Try to write file
            try:
                self.log(f"     💾 Writing to file...")
                with open(filepath, 'wb') as f:
                    if total_size == 0:
                        f.write(response.content)
                    else:
                        downloaded = 0
                        last_log = time.time()
                        chunk_count = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                chunk_count += 1
                                # Show progress every 2 seconds
                                if time.time() - last_log > 2:
                                    progress = (downloaded / total_size) * 100
                                    mb_downloaded = downloaded / (1024*1024)
                                    mb_total = total_size / (1024*1024)
                                    self.log(f"   Progress: {progress:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='\r')
                                    last_log = time.time()
                        
                        # Final flush only
                        self.log(f"\n     ✅ Write complete, flushing to disk...")
                        f.flush()
                        os.fsync(f.fileno())  # Force write to disk

            except OSError as e:
                import sys
                error_msg = f"💥 OSError while writing file: {str(e)}"
                self.log(f"     {error_msg}")
                self.log(f"     💥 Error code: {e.errno if hasattr(e, 'errno') else 'N/A'}")
                print(error_msg, file=sys.stderr)
                print(f"Error code: {e.errno if hasattr(e, 'errno') else 'N/A'}", file=sys.stderr)
                raise e
            except Exception as e:
                import sys
                error_msg = f"💥 Unexpected error while writing: {type(e).__name__}: {str(e)}"
                self.log(f"     {error_msg}")
                print(error_msg, file=sys.stderr)
                raise e
            
            self.log(f"\n✅ Downloaded: {os.path.basename(filepath)}")
            self.stats["downloaded_files"] += 1
            return True
            
        except requests.exceptions.RequestException as e:
            import sys
            error_msg = f"\n❌ Network error: {type(e).__name__}: {str(e)}"
            self.log(error_msg)
            print(error_msg, file=sys.stderr)
            self.stats["failed_downloads"] += 1
            self.stats["errors"].append(f"Network error for {url}: {str(e)}")
            return False
        except OSError as e:
            import sys
            error_msg = f"\n❌ File system error: {type(e).__name__}: {str(e)}"
            self.log(error_msg)
            self.log(f"❌ This may be a path length or permission issue")
            print(error_msg, file=sys.stderr)
            print(f"Path: {filepath}", file=sys.stderr)
            self.stats["failed_downloads"] += 1
            self.stats["errors"].append(f"OS error for {url}: {str(e)}")
            return False
        except Exception as e:
            import sys
            error_msg = f"\n❌ Download failed: {type(e).__name__}: {str(e)}"
            self.log(error_msg)
            print(error_msg, file=sys.stderr)
            print(f"URL: {url}", file=sys.stderr)
            print(f"Path: {filepath}", file=sys.stderr)
            self.stats["failed_downloads"] += 1
            self.stats["errors"].append(f"Download failed for {url}: {str(e)}")
            return False
    
    def fetch_transcript(self, resource_id, max_retries=3):
        """Fetch transcript from AI pipeline API with retry logic"""
        api_url = f"https://learning-ai.prod.karmayogibharat.net/api/kb-pipeline/v3/transcoder/stats?resource_id={resource_id}"
        
        for attempt in range(1, max_retries + 1):
            try:
                if attempt > 1:
                    wait_time = 2 ** (attempt - 1)
                    self.log(f"     ⏱️  Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    self.log(f"     🔄 Retry attempt {attempt}/{max_retries}")
                
                self.log(f"     📡 Fetching transcript from AI pipeline...")
                response = requests.get(api_url, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                self.log(f"     ✅ Transcript data received")
                self.log(f"     🔍 DEBUG: Response type: {type(data)}")
                if isinstance(data, dict):
                    self.log(f"     🔍 DEBUG: Response keys: {list(data.keys())}")
                return data
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries:
                    self.log(f"     ⚠️  Attempt {attempt} failed: {str(e)}")
                else:
                    self.log(f"     ❌ All {max_retries} attempts failed: {str(e)}")
                    self.stats["transcript_errors"] += 1
                    self.stats["errors"].append(f"Transcript fetch failed for {resource_id}: {str(e)}")
                    return None
            except Exception as e:
                self.log(f"     ❌ Unexpected error: {str(e)}")
                self.stats["transcript_errors"] += 1
                self.stats["errors"].append(f"Transcript error for {resource_id}: {str(e)}")
                return None
        
        return None
    
    def download_vtt_file(self, vtt_url):
        """Download VTT file content from URL"""
        try:
            self.log(f"     ⬇️  Downloading VTT file...")
            response = requests.get(vtt_url, timeout=30)
            response.raise_for_status()
            
            # Return VTT content as text
            vtt_content = response.text
            self.log(f"     ✅ VTT file downloaded ({len(vtt_content)} chars)")
            return vtt_content
            
        except Exception as e:
            self.log(f"     ❌ Failed to download VTT: {str(e)}")
            return None
    
    def extract_youtube_id(self, url):
        """Extract YouTube video ID from URL"""
        try:
            # Handle different YouTube URL formats
            # https://www.youtube.com/watch?v=VIDEO_ID
            # https://youtu.be/VIDEO_ID
            # https://youtube.com/embed/VIDEO_ID
            
            parsed_url = urlparse(url)
            
            if 'youtube.com' in parsed_url.netloc:
                if parsed_url.path == '/watch':
                    query_params = parse_qs(parsed_url.query)
                    return query_params.get('v', [None])[0]
                elif parsed_url.path.startswith('/embed/'):
                    return parsed_url.path.split('/embed/')[1].split('?')[0]
            elif 'youtu.be' in parsed_url.netloc:
                return parsed_url.path[1:].split('?')[0]
            
            return None
            
        except Exception as e:
            self.log(f"     ❌ Failed to extract YouTube ID: {str(e)}")
            return None
    
    def fetch_youtube_transcript(self, video_url):
        """Fetch transcript from YouTube video"""
        if not YOUTUBE_API_AVAILABLE:
            self.log(f"     ⚠️  YouTube transcript API not available")
            return None
        
        try:
            # Rate limiting: Add delay between YouTube requests
            time_since_last = time.time() - self.last_youtube_request
            if self.last_youtube_request > 0 and time_since_last < self.youtube_request_delay:
                wait_time = self.youtube_request_delay - time_since_last
                self.log(f"     ⏱️  Rate limit delay: waiting {wait_time:.1f}s before YouTube request...")
                time.sleep(wait_time)
            
            # Extract video ID
            video_id = self.extract_youtube_id(video_url)
            
            if not video_id:
                self.log(f"     ❌ Could not extract video ID from URL")
                return None
            
            self.log(f"     📹 Fetching YouTube transcript for video: {video_id}")
            self.last_youtube_request = time.time()  # Track request time
            
            # Import and use the API correctly
            from youtube_transcript_api import YouTubeTranscriptApi as YT_API
            
            # Create instance and fetch transcript - fetch is an instance method
            yt_api = YT_API()
            transcript = yt_api.fetch(video_id, ['en'])
            
            # The fetch method returns a list of transcript items
            if transcript:
                # Combine transcript items into readable text
                if isinstance(transcript, list):
                    text = " ".join([item.get('text', '') for item in transcript])
                else:
                    text = str(transcript)
                
                self.log(f"     ✅ YouTube transcript fetched ({len(text)} chars)")
                return text
            else:
                self.log(f"     ⚠️ No transcript data returned")
                return None
            
        except Exception as e:
            error_str = str(e)
            # Check if it's a YouTube blocking error
            if "Could not retrieve a transcript" in error_str or "blocked" in error_str.lower():
                self.log(f"     ⚠️  YouTube transcript unavailable (YouTube may be blocking requests)")
                self.log(f"     💡 This is a YouTube limitation, not an error in the downloader")
            else:
                self.log(f"     ❌ YouTube transcript error: {error_str[:100]}")
            
            self.stats["transcript_errors"] += 1
            return None
    
    def save_transcript(self, transcript_data, resource_folder, resource_do_id, resource_name, transcript_type="json"):
        """Save transcript data to text file"""
        try:
            # Create filename
            sanitized_name = self.sanitize_filename(resource_name)[:25]
            
            # Different filename based on type
            if transcript_type == "vtt":
                transcript_filename = f"transcript_en_{sanitized_name}_{resource_do_id[-10:]}.txt"
            elif transcript_type == "youtube":
                transcript_filename = f"transcript_youtube_{sanitized_name}_{resource_do_id[-10:]}.txt"
            else:
                transcript_filename = f"transcript_{sanitized_name}_{resource_do_id[-10:]}.txt"
            
            transcript_path = os.path.normpath(os.path.join(resource_folder, transcript_filename))
            
            self.log(f"     💾 Saving transcript to: {transcript_filename}")
            
            # Format the transcript data as readable text
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"Transcript for Resource: {resource_name}\n")
                f.write(f"Resource ID: {resource_do_id}\n")
                f.write(f"Type: {transcript_type.upper()}\n")
                f.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                # Write content based on type
                if transcript_type == "vtt" or transcript_type == "youtube":
                    # Plain text for VTT and YouTube
                    f.write(transcript_data)
                else:
                    # JSON for API responses
                    f.write(json.dumps(transcript_data, indent=2, ensure_ascii=False))
            
            self.log(f"     ✅ Transcript saved successfully")
            self.stats["transcripts_fetched"] += 1
            return True
            
        except Exception as e:
            self.log(f"     ❌ Failed to save transcript: {str(e)}")
            self.stats["transcript_errors"] += 1
            self.stats["errors"].append(f"Failed to save transcript for {resource_do_id}: {str(e)}")
            return False
    
    def process_resource(self, resource_do_id, course_folder, course_name=""):
        """Process individual resource and download if SCORM"""
        self.log(f"\n  🔍 Checking resource: {resource_do_id}")
        
        resource_details = self.get_content_details(resource_do_id)
        
        if not resource_details:
            return
        
        mime_type = resource_details.get("mimeType", "")
        resource_name = resource_details.get("name", "Untitled")
        
        self.log(f"     Name: {resource_name}")
        self.log(f"     MimeType: {mime_type}")
        
        # Check if it's a SCORM file
        if mime_type == "application/vnd.ekstep.html-archive":
            self.log(f"     ✨ SCORM file detected!")
            self.stats["total_scorm_files"] += 1
            
            # Use module name + DO ID for resource folder
            sanitized_module_name = self.sanitize_filename(resource_name)[:25]
            resource_folder_name = f"{sanitized_module_name}_{resource_do_id[-10:]}"
            resource_folder_path = os.path.normpath(os.path.join(course_folder, resource_folder_name))
            
            Path(resource_folder_path).mkdir(parents=True, exist_ok=True)
            
            # Get actual folder path
            actual_folder_path = os.path.abspath(resource_folder_path)
            
            # Get artifact URL
            artifact_url = resource_details.get("artifactUrl", "")
            
            if artifact_url:
                # Convert URL
                download_url = self.convert_storage_url(artifact_url)
                self.log(f"     📥 Download URL: {download_url}")
                
                # Use sanitized module name + DO ID for ZIP file
                file_ext = ".zip"  # SCORM files are always ZIP
                zip_filename = f"{sanitized_module_name}_{resource_do_id[-10:]}{file_ext}"
                filepath = os.path.normpath(os.path.join(actual_folder_path, zip_filename))
                
                # Log full path for debugging
                if len(filepath) > 200:
                    self.log(f"     ⚠️ Path length: {len(filepath)} chars")
                
                # Download file with retry logic
                success = self.download_file_with_retry(download_url, filepath)
                
            else:
                self.log(f"     ⚠️ No artifact URL found")
        
        # Check if it's an MP4 file
        elif mime_type == "video/mp4":
            self.log(f"     🎥 MP4 video detected!")
            self.stats["total_mp4_files"] += 1
            
            # Create resource folder for MP4
            sanitized_module_name = self.sanitize_filename(resource_name)[:25]
            resource_folder_name = f"{sanitized_module_name}_{resource_do_id[-10:]}"
            resource_folder_path = os.path.normpath(os.path.join(course_folder, resource_folder_name))
            
            Path(resource_folder_path).mkdir(parents=True, exist_ok=True)
            
            # Fetch transcript from AI pipeline
            self.log(f"     📝 Fetching transcript for MP4...")
            transcript_data = self.fetch_transcript(resource_do_id)
            
            if transcript_data:
                # Check if response contains VTT files
                vtt_files = []
                if isinstance(transcript_data, dict):
                    # Look for data array first
                    data_array = None
                    
                    if 'data' in transcript_data and isinstance(transcript_data['data'], list):
                        data_array = transcript_data['data']
                    elif 'result' in transcript_data and isinstance(transcript_data['result'], list):
                        data_array = transcript_data['result']
                    elif isinstance(transcript_data, list):
                        data_array = transcript_data
                    
                    # Extract transcripts from data array
                    all_transcripts = []
                    
                    if data_array:
                        self.log(f"     📦 Found {len(data_array)} data item(s)")
                        for data_item in data_array:
                            if isinstance(data_item, dict):
                                # Look for transcription_urls (plural) or transcription_url (singular)
                                transcript_urls = None
                                
                                if 'transcription_urls' in data_item:
                                    transcript_urls = data_item['transcription_urls']
                                elif 'transcription_url' in data_item:
                                    transcript_urls = data_item['transcription_url']
                                elif 'transcripts' in data_item:
                                    transcript_urls = data_item['transcripts']
                                
                                if transcript_urls and isinstance(transcript_urls, list):
                                    all_transcripts.extend(transcript_urls)
                    else:
                        # Fallback: try direct access to transcription fields
                        for key in ['transcription_urls', 'transcription_url', 'transcripts']:
                            if key in transcript_data and isinstance(transcript_data[key], list):
                                all_transcripts = transcript_data[key]
                                break
                    
                    # Now filter for English VTT files
                    if all_transcripts:
                        self.log(f"     📋 Found {len(all_transcripts)} transcript entries")
                        
                        for idx, item in enumerate(all_transcripts):
                            if isinstance(item, dict):
                                item_type = item.get('type', '')
                                item_lang = item.get('language', '')
                                
                                self.log(f"        - Type: {item_type}, Language: {item_lang}")
                                
                                # Check for English language (case-insensitive)
                                if item_type == 'vtt' and item_lang.lower() in ['english', 'en']:
                                    vtt_files.append(item)
                    else:
                        self.log(f"     ⚠️  No transcript entries found in response")
                    
                if vtt_files:
                    # Download English VTT file
                    self.log(f"     📄 Found {len(vtt_files)} English VTT file(s)")
                    for vtt_file in vtt_files:
                        # Try both 'url' and 'uri' field names
                        vtt_url = vtt_file.get('url') or vtt_file.get('uri')
                        if vtt_url:
                            self.log(f"     🔗 VTT URL: {vtt_url[:80]}...")
                            vtt_content = self.download_vtt_file(vtt_url)
                            if vtt_content:
                                self.save_transcript(vtt_content, resource_folder_path, resource_do_id, resource_name, transcript_type="vtt")
                else:
                    # Save JSON response as fallback
                    self.log(f"     📄 No English VTT files found, saving JSON response")
                    self.save_transcript(transcript_data, resource_folder_path, resource_do_id, resource_name)
            else:
                self.log(f"     ⚠️ No transcript data available")
        
        # Check if it's a YouTube video (x-url mime type)
        elif mime_type == "x-url" or "youtube.com" in str(resource_details.get("artifactUrl", "")).lower() or "youtu.be" in str(resource_details.get("artifactUrl", "")).lower():
            self.log(f"     📹 YouTube video detected!")
            
            # Create resource folder
            sanitized_module_name = self.sanitize_filename(resource_name)[:25]
            resource_folder_name = f"{sanitized_module_name}_{resource_do_id[-10:]}"
            resource_folder_path = os.path.normpath(os.path.join(course_folder, resource_folder_name))
            
            Path(resource_folder_path).mkdir(parents=True, exist_ok=True)
            
            # Get YouTube URL from artifactUrl
            youtube_url = resource_details.get("artifactUrl", "")
            
            if youtube_url:
                self.log(f"     📝 Fetching YouTube transcript...")
                transcript_text = self.fetch_youtube_transcript(youtube_url)
                
                if transcript_text:
                    self.save_transcript(transcript_text, resource_folder_path, resource_do_id, resource_name, transcript_type="youtube")
                else:
                    self.log(f"     ⚠️ Could not fetch YouTube transcript")
            else:
                self.log(f"     ⚠️ No YouTube URL found")
        
        else:
            self.log(f"     ⏭️  Not a SCORM or MP4 file (Type: {mime_type}), skipping")
    
    def process_course(self, course_do_id):
        """Process a single course"""
        self.log(f"\n{'='*80}")
        self.log(f"🎓 Processing Course: {course_do_id}")
        self.log(f"{'='*80}")
        
        # Get course details
        course_details = self.get_content_details(course_do_id)
        
        if not course_details:
            self.log(f"❌ Failed to fetch course details")
            return
        
        course_name = course_details.get("name", "Untitled_Course")
        child_nodes = course_details.get("childNodes", [])
        
        self.log(f"📚 Course Name: {course_name}")
        self.log(f"📦 Total Resources: {len(child_nodes)}")
        
        # Use course name (20 chars) + DO ID
        sanitized_course_name = self.sanitize_filename(course_name)[:20]
        course_folder_name = f"{sanitized_course_name}_{course_do_id[-15:]}"
        course_folder_path = os.path.normpath(os.path.join(self.download_folder, course_folder_name))
        
        Path(course_folder_path).mkdir(parents=True, exist_ok=True)
        
        # Process each resource
        for idx, resource_do_id in enumerate(child_nodes, 1):
            self.log(f"\n  📌 Resource {idx}/{len(child_nodes)}")
            self.process_resource(resource_do_id, course_folder_path, course_name)
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.5)
        
        self.stats["processed_courses"] += 1
        
        # Update external status if callback exists (for web UI)
        if hasattr(self, 'update_status_callback') and self.update_status_callback:
            self.update_status_callback(self.stats)
    
    def process_multiple_courses(self, course_do_ids):
        """Process multiple courses"""
        self.stats["total_courses"] = len(course_do_ids)
        
        self.log(f"\n🚀 Starting SCORM Downloader")
        self.log(f"📊 Total Courses to Process: {len(course_do_ids)}")
        self.log(f"💾 Download Location: {os.path.abspath(self.download_folder)}")
        
        for idx, course_do_id in enumerate(course_do_ids, 1):
            self.log(f"\n\n{'#'*80}")
            self.log(f"# Course {idx}/{len(course_do_ids)}")
            self.log(f"{'#'*80}")
            
            try:
                self.process_course(course_do_id)
            except Exception as e:
                self.log(f"\n❌ Failed to process course {course_do_id}: {str(e)}")
                self.stats["errors"].append(f"Course {course_do_id}: {str(e)}")
            
            # Add delay between courses
            if idx < len(course_do_ids):
                self.log(f"\n⏳ Waiting before next course...")
                time.sleep(2)
        
        self.print_summary()
    
    def print_summary(self):
        """Print download summary"""
        self.log(f"\n\n{'='*80}")
        self.log(f"📊 DOWNLOAD SUMMARY")
        self.log(f"{'='*80}")
        self.log(f"✅ Total Courses Processed: {self.stats['processed_courses']}/{self.stats['total_courses']}")
        self.log(f"📦 Total SCORM Files Found: {self.stats['total_scorm_files']}")
        self.log(f"⬇️  Successfully Downloaded: {self.stats['downloaded_files']}")
        self.log(f"❌ Failed Downloads: {self.stats['failed_downloads']}")
        self.log(f"🎥 Total MP4 Files Found: {self.stats['total_mp4_files']}")
        self.log(f"📝 Transcripts Fetched: {self.stats['transcripts_fetched']}")
        self.log(f"❌ Transcript Errors: {self.stats['transcript_errors']}")
        
        if self.stats["errors"]:
            self.log(f"\n⚠️  Errors Encountered: {len(self.stats['errors'])}")
            self.log("\nError Details:")
            for error in self.stats["errors"][:10]:
                self.log(f"  - {error}")
            if len(self.stats["errors"]) > 10:
                self.log(f"  ... and {len(self.stats['errors']) - 10} more errors")
        
        self.log(f"\n💾 All files saved to: {os.path.abspath(self.download_folder)}")
        self.log(f"{'='*80}\n")


def main():
    """Main execution function"""
    
    # Default list just for fallback
    course_do_ids = []
    
    # Create downloader instance
    downloader = SCORMDownloader()
    pass


if __name__ == "__main__":
    main()
