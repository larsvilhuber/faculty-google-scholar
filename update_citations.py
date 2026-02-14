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
import sys
from datetime import datetime, timedelta
from scholarly import scholarly
from typing import List, Dict, Optional
import time
import statistics


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


def needs_update(as_of_date: str, update_delay_days: int) -> bool:
    """
    Check if a faculty member's data needs updating based on the last update date.
    
    Args:
        as_of_date: Date string in YYYY-MM-DD format
        update_delay_days: Minimum days before re-updating
        
    Returns:
        True if data needs updating, False otherwise
    """
    if not as_of_date or not as_of_date.strip():
        return True  # No date means never updated
    
    try:
        last_update = datetime.strptime(as_of_date.strip(), '%Y-%m-%d')
        today = datetime.now()
        days_since_update = (today - last_update).days
        
        return days_since_update >= update_delay_days
    except ValueError:
        # Invalid date format, treat as needing update
        return True


def countdown_timer(seconds: float) -> None:
    """
    Display a countdown timer.
    
    Args:
        seconds: Number of seconds to count down
    """
    for remaining in range(int(seconds), 0, -1):
        mins, secs = divmod(remaining, 60)
        timeformat = f'{mins:02d}:{secs:02d}' if mins > 0 else f'{secs} sec'
        sys.stdout.write(f'\r      Waiting {timeformat} before next query...')
        sys.stdout.flush()
        time.sleep(1)
    
    # Handle fractional seconds
    fractional = seconds - int(seconds)
    if fractional > 0:
        time.sleep(fractional)
    
    sys.stdout.write('\r' + ' ' * 60 + '\r')  # Clear the line
    sys.stdout.flush()


def update_citations(data: List[Dict[str, str]], csv_path: str, delay: float = 30.0, 
                     update_delay_days: int = 7) -> List[Dict[str, str]]:
    """
    Update citation counts and h-index for all faculty with scholar_id.
    
    Args:
        data: List of faculty records
        csv_path: Path to CSV file for incremental saves
        delay: Delay between requests (seconds) to avoid rate limiting
        update_delay_days: Skip entries updated within this many days
        
    Returns:
        Updated list of faculty records
    """
    updated_count = 0
    skipped_count = 0
    skipped_recent = 0
    error_count = 0
    first_query = True
    today = datetime.now().strftime('%Y-%m-%d')
    
    print(f"\nStarting update process...")
    print(f"Date: {today}")
    print(f"Skipping entries updated within {update_delay_days} days\n")
    
    for i, faculty in enumerate(data):
        scholar_id = faculty.get('scholar_id', '').strip()
        name = faculty['name']
        
        # Skip if no scholar_id
        if not scholar_id:
            print(f"  [{i+1}/{len(data)}] ⊘ Skipping {name} (no scholar_id)")
            skipped_count += 1
            continue
        
        # Check if recently updated
        if not needs_update(faculty.get('as_of_date', ''), update_delay_days):
            as_of = faculty.get('as_of_date', '')
            print(f"  [{i+1}/{len(data)}] ⊘ Skipping {name} (updated {as_of})")
            skipped_recent += 1
            continue
        
        # Add delay before this query (but not the first one)
        if not first_query:
            countdown_timer(delay)
        
        print(f"  [{i+1}/{len(data)}] Updating {name}...", end=' ')
        sys.stdout.flush()  # Ensure output appears immediately before long-running query
        
        # Get current metrics from Google Scholar
        metrics = get_scholar_metrics(scholar_id)
        
        if metrics:
            old_citations = faculty.get('citations', 'N/A')
            old_h_index = faculty.get('h_index', 'N/A')
            
            faculty['citations'] = str(metrics['citations'])
            faculty['h_index'] = str(metrics['h_index'])
            faculty['as_of_date'] = today
            
            # Save immediately after each update
            save_faculty_data(csv_path, data)
            
            print(f"✓")
            print(f"      Citations: {old_citations} → {metrics['citations']}")
            print(f"      H-index: {old_h_index} → {metrics['h_index']}")
            
            updated_count += 1
            first_query = False  # Mark that we've done at least one query
        else:
            print(f"✗ Error")
            error_count += 1
            first_query = False  # Even on error, mark that we attempted a query
    
    print(f"\n{'='*70}")
    print(f"Update Summary:")
    print(f"  Successfully updated: {updated_count}")
    print(f"  Skipped (no scholar_id): {skipped_count}")
    print(f"  Skipped (recently updated): {skipped_recent}")
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
        h_index_list = [int(f['h_index']) for f in data if f.get('h_index', '').strip() and f['h_index'].isdigit()]
        
        if citations_list:
            print(f"\nCitation Statistics:")
            print(f"  Total citations: {sum(citations_list):,}")
            print(f"  Average citations: {sum(citations_list)/len(citations_list):,.0f}")
            print(f"  Median citations: {statistics.median(citations_list):,.0f}")
            print(f"  Max citations: {max(citations_list):,}")
            print(f"  Min citations: {min(citations_list):,}")
        
        if h_index_list:
            print(f"\nH-Index Statistics:")
            print(f"  Average h-index: {sum(h_index_list)/len(h_index_list):,.1f}")
            print(f"  Median h-index: {statistics.median(h_index_list):,.0f}")
            print(f"  Max h-index: {max(h_index_list)}")
            print(f"  Min h-index: {min(h_index_list)}")


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
        '--query-delay',
        type=float,
        default=30.0,
        help='Delay between requests in seconds (default: 30.0 to avoid rate limiting)'
    )
    parser.add_argument(
        '--update-delay-days',
        type=int,
        default=7,
        help='Skip entries updated within this many days (default: 7)'
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
    
    print(f"\nConfiguration:")
    print(f"  Query delay: {args.query_delay} seconds (time between Google Scholar requests)")
    print(f"  Update delay: {args.update_delay_days} days (skip entries updated within this period)")
    
    print(f"\nLoading faculty data from {args.csv}...")
    data = load_faculty_data(args.csv)
    print(f"Loaded {len(data)} faculty records")
    
    if args.stats_only:
        show_statistics(data)
        return
    
    # Count how many will be updated
    with_scholar_id = [f for f in data if f.get('scholar_id', '').strip()]
    needs_updating = [f for f in with_scholar_id 
                     if needs_update(f.get('as_of_date', ''), args.update_delay_days)]
    to_update = len(needs_updating)
    
    if len(with_scholar_id) == 0:
        print("\n⚠ No faculty members have Google Scholar IDs!")
        print("Please run find_scholar_ids.py first to populate scholar IDs.")
        return
    
    if to_update == 0:
        print(f"\n✓ All {len(with_scholar_id)} faculty with scholar IDs were updated within the last {args.update_delay_days} days.")
        print(f"Use --update-delay-days 0 to force update all entries.")
        return
    
    print(f"\nWill update {to_update} faculty members (out of {len(with_scholar_id)} with Google Scholar IDs)")
    print(f"Skipping {len(with_scholar_id) - to_update} recently updated (within {args.update_delay_days} days)")
    print(f"(Estimated time: ~{to_update * args.query_delay / 60:.1f} minutes)\n")
    
    response = input("Continue? (y/n): ").strip().lower()
    if response != 'y':
        print("Cancelled.")
        return
    
    # Update citations
    updated_data = update_citations(data, csv_path=args.csv, delay=args.query_delay, 
                                   update_delay_days=args.update_delay_days)
    
    # Final save to ensure everything is persisted
    save_faculty_data(args.csv, updated_data)
    
    # Show statistics
    show_statistics(updated_data)
    
    print("\nDone!")


if __name__ == '__main__':
    main()
