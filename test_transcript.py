"""
Test script to verify transcript fetching functionality
"""

from scorm_downloader import SCORMDownloader
import os
import shutil

def test_transcript_fetching():
    """Test the transcript fetching feature with a sample resource ID"""
    
    print("=" * 80)
    print("🧪 Testing Transcript Fetching Feature")
    print("=" * 80)
    
    # Create a test downloader instance
    downloader = SCORMDownloader()
    downloader.download_folder = "test_transcripts"
    
    # Clean up test folder if it exists
    if os.path.exists("test_transcripts"):
        shutil.rmtree("test_transcripts")
    
    os.makedirs("test_transcripts", exist_ok=True)
    
    # Test fetching a transcript (using a sample resource ID)
    # You can replace this with an actual MP4 resource ID
    test_resource_id = "do_1234567890"  # Replace with real resource ID
    
    print(f"\n📝 Testing transcript fetch for resource: {test_resource_id}")
    transcript_data = downloader.fetch_transcript(test_resource_id)
    
    if transcript_data:
        print("✅ Transcript data received successfully!")
        print(f"📊 Data preview: {str(transcript_data)[:200]}...")
        
        # Test saving transcript
        test_folder = "test_transcripts/sample_folder"
        os.makedirs(test_folder, exist_ok=True)
        
        success = downloader.save_transcript(
            transcript_data, 
            test_folder, 
            test_resource_id, 
            "Test Resource"
        )
        
        if success:
            print("✅ Transcript saved successfully!")
            # List files in test folder
            files = os.listdir(test_folder)
            print(f"📁 Files created: {files}")
        else:
            print("❌ Failed to save transcript")
    else:
        print("⚠️ No transcript data received (this is expected if the resource ID doesn't exist)")
    
    print("\n" + "=" * 80)
    print("📊 Test Statistics:")
    print(f"   MP4 Files: {downloader.stats['total_mp4_files']}")
    print(f"   Transcripts Fetched: {downloader.stats['transcripts_fetched']}")
    print(f"   Transcript Errors: {downloader.stats['transcript_errors']}")
    print("=" * 80)
    
    # Clean up
    if os.path.exists("test_transcripts"):
        shutil.rmtree("test_transcripts")
        print("\n🗑️ Cleaned up test folder")

if __name__ == "__main__":
    print("""
    ⚠️  NOTE: This is a basic test script.
    
    To properly test the transcript fetching feature:
    1. Replace 'test_resource_id' with an actual MP4 resource DO ID
    2. Or use the web UI to download a course containing MP4 files
    3. Check the logs for transcript fetching messages
    4. Verify transcript files are created in the download folder
    
    The feature is integrated into the main download process and will
    automatically fetch transcripts for all MP4 resources found.
    """)
    
    test_transcript_fetching()
