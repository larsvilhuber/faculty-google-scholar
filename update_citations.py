#!/usr/bin/env python3
"""
Update Google Scholar citations and h-index for faculty members.

This script reads faculty members with Google Scholar IDs from the CSV file
and updates their citation counts and h-index with current data from Google Scholar.

Usage:
    python update_citations.py [--csv FILENAME]
"""

import csv
import argparse
from datetime import datetime
from scholarly import scholarly
from typing import List, Dict, Optional
import time


def load_faculty_data(csv_path: str) -> List[Dict[str, str]]:
    """
    Load faculty data from CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of faculty records as dictionaries
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def save_faculty_data(csv_path: str, data: List[Dict[str, str]]) -> None:
    """
    Save updated faculty data to CSV file.
    
    Args:
        csv_path: Path to the CSV file
        data: List of faculty records
    """
    fieldnames = ['name', 'scholar_id', 'citations', 'h_index', 'as_of_date']
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"\nData saved to {csv_path}")


def get_scholar_metrics(scholar_id: str) -> Optional[Dict[str, any]]:
    """
    Retrieve current citation metrics for a Google Scholar profile.
    
    Args:
        scholar_id: Google Scholar author ID
        
    Returns:
        Dictionary with citations and h_index, or None if error
    """
    try:
        author = scholarly.search_author_id(scholar_id)
        
        # Fill in author details to get complete information
        author_filled = scholarly.fill(author)
        
        # Extract citation metrics
        citations = author_filled.get('citedby', 0)
        h_index = author_filled.get('hindex', 0)
        
        return {
            'citations': citations,
            'h_index': h_index
        }
    
    except Exception as e:
        print(f"  ✗ Error retrieving data for scholar_id {scholar_id}: {e}")
        return None


def update_citations(data: List[Dict[str, str]], delay: float = 1.0) -> List[Dict[str, str]]:
    """
    Update citation counts and h-index for all faculty with scholar_id.
    
    Args:
        data: List of faculty records
        delay: Delay between requests (seconds) to avoid rate limiting
        
    Returns:
        Updated list of faculty records
    """
    updated_count = 0
    skipped_count = 0
    error_count = 0
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\nStarting update process...")
    print(f"Date: {today}\n")
    
    for i, faculty in enumerate(data):
        scholar_id = faculty.get('scholar_id', '').strip()
        name = faculty['name']
        
        # Skip if no scholar_id
        if not scholar_id:
            print(f"  [{i+1}/{len(data)}] ⊘ Skipping {name} (no scholar_id)")
            skipped_count += 1
            continue
        
        print(f"  [{i+1}/{len(data)}] Updating {name}...", end=' ')
        
        # Get current metrics from Google Scholar
        metrics = get_scholar_metrics(scholar_id)
        
        if metrics:
            old_citations = faculty.get('citations', 'N/A')
            old_h_index = faculty.get('h_index', 'N/A')
            
            faculty['citations'] = str(metrics['citations'])
            faculty['h_index'] = str(metrics['h_index'])
            faculty['as_of_date'] = today
            
            print(f"✓")
            print(f"      Citations: {old_citations} → {metrics['citations']}")
            print(f"      H-index: {old_h_index} → {metrics['h_index']}")
            
            updated_count += 1
        else:
            print(f"✗ Error")
            error_count += 1
        
        # Add delay to avoid rate limiting
        if i < len(data) - 1:  # Don't delay after the last one
            time.sleep(delay)
    
    print(f"\n{'='*70}")
    print(f"Update Summary:")
    print(f"  Successfully updated: {updated_count}")
    print(f"  Skipped (no scholar_id): {skipped_count}")
    print(f"  Errors: {error_count}")
    print(f"{'='*70}\n")
    
    return data


def show_statistics(data: List[Dict[str, str]]) -> None:
    """
    Display statistics about the dataset.
    
    Args:
        data: List of faculty records
    """
    total = len(data)
    with_id = sum(1 for f in data if f.get('scholar_id', '').strip())
    with_citations = sum(1 for f in data if f.get('citations', '').strip())
    
    print(f"\nDataset Statistics:")
    print(f"  Total faculty: {total}")
    print(f"  With Google Scholar ID: {with_id} ({100*with_id/total:.1f}%)")
    print(f"  With citation data: {with_citations} ({100*with_citations/total:.1f}%)")
    
    if with_citations > 0:
        citations_list = [int(f['citations']) for f in data if f.get('citations', '').strip() and f['citations'].isdigit()]
        if citations_list:
            print(f"\nCitation Statistics:")
            print(f"  Total citations: {sum(citations_list):,}")
            print(f"  Average citations: {sum(citations_list)/len(citations_list):,.0f}")
            print(f"  Max citations: {max(citations_list):,}")
            print(f"  Min citations: {min(citations_list):,}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Update Google Scholar citation metrics for faculty members'
    )
    parser.add_argument(
        '--csv',
        default='faculty_scholar_data.csv',
        help='Path to the CSV file (default: faculty_scholar_data.csv)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )
    parser.add_argument(
        '--stats-only',
        action='store_true',
        help='Only show statistics without updating'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("Google Scholar Citation Update Tool")
    print("="*70)
    
    print(f"\nLoading faculty data from {args.csv}...")
    data = load_faculty_data(args.csv)
    print(f"Loaded {len(data)} faculty records")
    
    if args.stats_only:
        show_statistics(data)
        return
    
    # Count how many will be updated
    to_update = sum(1 for f in data if f.get('scholar_id', '').strip())
    
    if to_update == 0:
        print("\n⚠ No faculty members have Google Scholar IDs!")
        print("Please run find_scholar_ids.py first to populate scholar IDs.")
        return
    
    print(f"\nWill update {to_update} faculty members with Google Scholar IDs")
    print(f"(Estimated time: ~{to_update * args.delay / 60:.1f} minutes)\n")
    
    response = input("Continue? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return
    
    # Update citations
    updated_data = update_citations(data, delay=args.delay)
    
    # Save updated data
    save_faculty_data(args.csv, updated_data)
    
    # Show statistics
    show_statistics(updated_data)
    
    print("\nDone!")


if __name__ == '__main__':
    main()
