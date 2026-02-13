"""
Extract faculty data from the Cornell faculty summaries document.
This script creates the initial CSV dataset with Google Scholar information.
"""

from docx import Document
import csv
import re
from datetime import datetime

def extract_faculty_data(docx_path):
    """
    Extract faculty names and Google Scholar metrics from the Word document.
    
    Args:
        docx_path: Path to the Word document containing faculty summaries
        
    Returns:
        List of dictionaries containing faculty data
    """
    doc = Document(docx_path)
    faculty_list = []
    current_faculty = None
    
    for para in doc.paragraphs:
        text = para.text.strip()
        
        if not text:
            continue
            
        # Check if this is a faculty name (lines that don't start with common section headers)
        # and are not too long
        if (not text.startswith(('Current Appointment', 'PhD Year', 'Fields of Interest', 
                                 'Short Bio:', 'Examples of Publications', 'Google Scholar',
                                 'External Funding', 'Public Outreach:', 'Notes:', 
                                 'Cornell Department', 'Faculty Summaries')) 
            and len(text) < 100 
            and not text[0].isdigit()
            and not text.startswith('"')
            and not text.startswith('•')):
            # Heuristic: Names are typically standalone paragraphs
            # Check if it could be a name (contains letters, possibly spaces)
            if re.match(r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)+$', text):
                # Save previous faculty if exists
                if current_faculty:
                    faculty_list.append(current_faculty)
                
                # Start new faculty entry
                current_faculty = {
                    'name': text,
                    'citations': '',
                    'h_index': '',
                    'scholar_id': '',
                    'as_of_date': ''
                }
        
        # Extract Google Scholar metrics
        elif text.startswith('Google Scholar Citations:') and current_faculty:
            # Parse: "Google Scholar Citations: 2,163     Google Scholar H-index: 16"
            match = re.search(r'Citations:\s*([\d,]+)\s*.*H-index:\s*(\d+)', text)
            if match:
                current_faculty['citations'] = match.group(1).replace(',', '')
                current_faculty['h_index'] = match.group(2)
                current_faculty['as_of_date'] = '2025-11-15'  # From the notes section
    
    # Don't forget the last faculty member
    if current_faculty:
        faculty_list.append(current_faculty)
    
    return faculty_list

def save_to_csv(faculty_list, csv_path):
    """
    Save faculty data to CSV file.
    
    Args:
        faculty_list: List of faculty dictionaries
        csv_path: Path to output CSV file
    """
    fieldnames = ['name', 'scholar_id', 'citations', 'h_index', 'as_of_date']
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for faculty in faculty_list:
            writer.writerow(faculty)
    
    print(f"Data saved to {csv_path}")
    print(f"Total faculty members: {len(faculty_list)}")

if __name__ == '__main__':
    # Extract data from document
    faculty_data = extract_faculty_data('cornell-faculty-summaries.docx')
    
    # Save to CSV
    save_to_csv(faculty_data, 'faculty_scholar_data.csv')
    
    # Print summary
    print("\nExtracted faculty:")
    for faculty in faculty_data:
        print(f"  {faculty['name']}: Citations={faculty['citations']}, H-index={faculty['h_index']}")
