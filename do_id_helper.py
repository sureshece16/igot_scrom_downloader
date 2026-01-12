#!/usr/bin/env python3
"""
Helper Script to Convert DO IDs from Various Formats
If you have course DO IDs in a text file, Excel, or other format,
this script can help convert them to the required Python list format.
"""

import re

def extract_do_ids_from_text(text):
    """Extract DO IDs from any text containing them"""
    # Pattern to match DO IDs (do_ followed by alphanumeric)
    pattern = r'do_\d+'
    do_ids = re.findall(pattern, text)
    return list(set(do_ids))  # Remove duplicates

def process_text_file(input_file):
    """Process a text file containing DO IDs"""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        do_ids = extract_do_ids_from_text(content)
        
        print(f"\n✅ Found {len(do_ids)} unique DO IDs in {input_file}")
        
        # Generate Python list format
        output = "COURSE_DO_IDS = [\n"
        for do_id in do_ids:
            output += f'    "{do_id}",\n'
        output += "]\n"
        
        # Save to a new file
        output_file = "extracted_course_ids.py"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        
        print(f"✅ Saved to: {output_file}")
        print("\nYou can now:")
        print(f"1. Review the {output_file} file")
        print("2. Copy the content to course_ids.py")
        print("3. Run: python run_downloader.py")
        
        return do_ids
        
    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' not found")
        return []
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return []

def process_manual_input():
    """Process DO IDs from manual input"""
    print("\n" + "="*80)
    print("Manual DO ID Input")
    print("="*80)
    print("\nPaste your DO IDs below (one per line or comma-separated)")
    print("Press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows) when done:\n")
    
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass
    
    text = "\n".join(lines)
    do_ids = extract_do_ids_from_text(text)
    
    if do_ids:
        print(f"\n✅ Found {len(do_ids)} DO IDs")
        
        # Generate Python list format
        output = "COURSE_DO_IDS = [\n"
        for do_id in do_ids:
            output += f'    "{do_id}",\n'
        output += "]\n"
        
        # Save to a new file
        output_file = "extracted_course_ids.py"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output)
        
        print(f"✅ Saved to: {output_file}")
        print("\nPreview:")
        print(output[:500] + "..." if len(output) > 500 else output)
    else:
        print("❌ No DO IDs found in the input")

def create_sample_format():
    """Create a sample text file showing the expected format"""
    sample = """# Sample DO IDs File
# You can list DO IDs in any of these formats:

# One per line:
do_113768226086068224132
do_113465506620735488151

# Comma-separated:
do_113768226086068224132, do_113465506620735488151, do_113768226086068224133

# In URLs:
https://portal.igotkarmayogi.gov.in/api/content/v1/read/do_113768226086068224132

# In JSON:
{"do_id": "do_113768226086068224132"}

# Mixed format - the script will extract all DO IDs automatically!
"""
    
    with open("sample_do_ids.txt", 'w', encoding='utf-8') as f:
        f.write(sample)
    
    print("✅ Created sample_do_ids.txt")
    print("   Edit this file with your DO IDs and run this script again")

def main():
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║              DO ID Extraction Helper                           ║
    ║                                                                ║
    ║  This script helps you convert DO IDs from various formats    ║
    ║  into the required Python list format for the downloader      ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    print("\nChoose an option:")
    print("1. Extract DO IDs from a text file")
    print("2. Paste DO IDs manually")
    print("3. Create a sample DO IDs file")
    print("4. Exit")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        filename = input("Enter the filename (e.g., do_ids.txt): ").strip()
        do_ids = process_text_file(filename)
        
        if do_ids:
            print("\nExtracted DO IDs:")
            for i, do_id in enumerate(do_ids[:10], 1):
                print(f"  {i}. {do_id}")
            if len(do_ids) > 10:
                print(f"  ... and {len(do_ids) - 10} more")
    
    elif choice == "2":
        process_manual_input()
    
    elif choice == "3":
        create_sample_format()
    
    elif choice == "4":
        print("Goodbye!")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()
