#!/usr/bin/env python3
"""
Find missing Google Scholar identifiers for faculty members.

This script searches Google Scholar for faculty members without a scholar_id
in the dataset. When multiple results are found, it presents the user with
options to choose the correct profile.

Usage:
    python find_scholar_ids.py [--csv FILENAME]
"""

import csv
import argparse
import sys
import urllib.parse
import time
import re
from typing import List, Dict, Optional
from difflib import SequenceMatcher
import requests
from bs4 import BeautifulSoup

try:
    from ddgs import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DDGS_AVAILABLE = True
    except ImportError:
        DDGS_AVAILABLE = False
        print("Warning: ddgs library not available")

try:
    from scholarly import scholarly
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False


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


def extract_scholar_id(url: str) -> Optional[str]:
    """
    Extract Google Scholar ID from a URL.
    
    Args:
        url: URL that may contain a scholar ID
        
    Returns:
        Scholar ID if found, None otherwise
    """
    # Look for user= parameter in URLs
    match = re.search(r'[?&]user=([^&]+)', url)
    if match:
        return match.group(1)
    return None


def get_name_from_profile(url: str, timeout: int = 5) -> Optional[str]:
    """
    Fetch a Google Scholar profile page and extract the name from the HTML.
    
    Args:
        url: URL of the Google Scholar profile
        timeout: Request timeout in seconds
        
    Returns:
        Name from the profile, or None if error
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Look for the name in the div with id="gsc_prf_in"
        name_div = soup.find('div', id='gsc_prf_in')
        if name_div:
            return name_div.get_text(strip=True)
        
        # Fallback: try to find it in the title
        title = soup.find('title')
        if title:
            # Title format is usually "Name - Google Scholar"
            title_text = title.get_text(strip=True)
            if ' - Google Scholar' in title_text:
                return title_text.replace(' - Google Scholar', '').strip()
        
        return None
    
    except Exception as e:
        # Silently fail - this is expected for some URLs
        return None


def normalize_name(name: str) -> str:
    """
    Normalize a name for comparison.
    
    Args:
        name: Name to normalize
        
    Returns:
        Normalized name (lowercase, no extra spaces, no punctuation)
    """
    # Remove common suffixes and titles
    name = re.sub(r'\b(Jr\.?|Sr\.?|III|II|IV|PhD|Ph\.D\.|Dr\.?|Prof\.?)\b', '', name, flags=re.IGNORECASE)
    # Remove punctuation except hyphens and apostrophes
    name = re.sub(r'[^\w\s\'-]', '', name)
    # Normalize whitespace
    name = ' '.join(name.split())
    return name.lower().strip()


def names_match(search_name: str, result_name: str, threshold: float = 0.85) -> bool:
    """
    Check if two names match well enough.
    
    Args:
        search_name: The name we're searching for
        result_name: The name from search results
        threshold: Similarity threshold (0-1)
        
    Returns:
        True if names match well enough
    """
    # Normalize both names
    search_norm = normalize_name(search_name)
    result_norm = normalize_name(result_name)
    
    # Exact match
    if search_norm == result_norm:
        return True
    
    # Split into parts
    search_parts = search_norm.split()
    result_parts = result_norm.split()
    
    # Need at least 2 parts (first and last name)
    if len(search_parts) < 2 or len(result_parts) < 2:
        return False
    
    # Last name MUST match exactly (most distinctive part)
    if search_parts[-1] != result_parts[-1]:
        return False
    
    # First name should match (exact or initial)
    search_first = search_parts[0]
    result_first = result_parts[0]
    
    # Allow initial matching (e.g., "J" matches "John")
    if len(search_first) == 1 or len(result_first) == 1:
        if search_first[0] != result_first[0]:
            return False
    else:
        # Full first names should be reasonably similar
        first_similarity = SequenceMatcher(None, search_first, result_first).ratio()
        if first_similarity < 0.8:
            return False
    
    # If we have middle names/initials, check them too
    if len(search_parts) > 2 or len(result_parts) > 2:
        # Middle parts should have some overlap
        search_middle = set(search_parts[1:-1])
        result_middle = set(result_parts[1:-1])
        
        # If both have middle names, at least one should match or be an initial
        if search_middle and result_middle:
            # Check if any middle part matches
            for sm in search_middle:
                for rm in result_middle:
                    if sm == rm or (len(sm) == 1 and sm[0] == rm[0]) or (len(rm) == 1 and rm[0] == sm[0]):
                        return True
            # No middle name match - be more cautious
            return False
    
    return True


def verify_profile_match(search_name: str, profile_url: str, scholar_id: str) -> Optional[Dict[str, str]]:
    """
    Fetch a Google Scholar profile and verify the name matches.
    
    Args:
        search_name: The name we're searching for
        profile_url: URL of the profile to check
        scholar_id: The scholar ID
        
    Returns:
        Dict with profile info if match, None otherwise
    """
    # Get the actual name from the profile page
    profile_name = get_name_from_profile(profile_url)
    
    if not profile_name:
        return None
    
    # Normalize both names for comparison
    search_norm = normalize_name(search_name)
    profile_norm = normalize_name(profile_name)
    
    # Check for exact match
    if search_norm == profile_norm:
        return {
            'scholar_id': scholar_id,
            'name': profile_name,
            'url': profile_url,
            'match_quality': 'exact'
        }
    
    # Check if names match with our matching logic
    if names_match(search_name, profile_name):
        return {
            'scholar_id': scholar_id,
            'name': profile_name,
            'url': profile_url,
            'match_quality': 'good'
        }
    
    return None


def search_web_for_scholar(name: str, keyword: str = '', max_results: int = 5, timeout: int = 10) -> List[Dict[str, str]]:
    """
    Search the web for Google Scholar profiles using DuckDuckGo.
    
    Args:
        name: Full name of the person to search
        keyword: Additional keyword for the search (e.g., institution name)
        max_results: Maximum number of results to return
        timeout: Timeout in seconds for the search
        
    Returns:
        List of dictionaries with scholar information
    """
    if not DDGS_AVAILABLE:
        return []
    
    try:
        # Use site-specific search for Google Scholar
        query = f"site:scholar.google.com/citations {name}"
        if keyword:
            query += f" {keyword}"
        
        verified_results = []
        seen_scholar_ids = set()  # Track seen IDs to avoid duplicates
        # Set a shorter timeout to avoid hanging
        with DDGS(timeout=timeout) as ddgs:
            search_results = list(ddgs.text(query, max_results=max_results * 3))  # Get more candidates
            
            print(f"  → Found {len(search_results)} search results, verifying names...")
            
            for result in search_results:
                url = result.get('href', '') or result.get('link', '')
                
                # Extract scholar ID from URL
                scholar_id = extract_scholar_id(url)
                
                if scholar_id and scholar_id not in seen_scholar_ids:
                    # Fetch the actual profile and verify the name
                    verified = verify_profile_match(name, url, scholar_id)
                    
                    if verified:
                        # Mark this scholar_id as seen
                        seen_scholar_ids.add(scholar_id)
                        # Get affiliation from the profile if possible
                        verified_results.append(verified)
                        
                        # Stop if we have enough verified results
                        if len(verified_results) >= max_results:
                            break
            
            print(f"  → {len(verified_results)} profile(s) with matching names")
        
        return verified_results
    
    except TimeoutError:
        print(f"  ⚠ Search timed out")
        return []
    except Exception as e:
        print(f"  ⚠ Search error: {type(e).__name__}")
        # Check if it's a rate limit error and inform user
        error_msg = str(e).lower()
        if '429' in error_msg or 'rate' in error_msg or 'too many' in error_msg:
            print(f"  ⚠ (Possible rate limiting - consider increasing --delay)")
        return []


def search_scholar_direct(name: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search Google Scholar directly (may be blocked).
    
    Args:
        name: Full name of the person to search
        max_results: Maximum number of results to return
        
    Returns:
        List of dictionaries with author information
    """
    if not SCHOLARLY_AVAILABLE:
        return []
    
    try:
        search_query = scholarly.search_author(name)
        results = []
        
        for i, author in enumerate(search_query):
            if i >= max_results:
                break
            
            # Extract key information
            scholar_id = author.get('scholar_id', '')
            author_name = author.get('name', '')
            affiliation = author.get('affiliation', '')
            interests = author.get('interests', [])
            url = f"https://scholar.google.com/citations?user={scholar_id}" if scholar_id else ''
            
            results.append({
                'scholar_id': scholar_id,
                'name': author_name,
                'affiliation': affiliation,
                'interests': ', '.join(interests[:5]) if interests else '',
                'url': url
            })
        
        return results
    
    except Exception as e:
        # Don't print error for every failure - this is expected
        return []


def get_search_url(name: str) -> str:
    """
    Generate Google Scholar search URL for manual searching.
    
    Args:
        name: Full name to search
        
    Returns:
        Google Scholar search URL
    """
    encoded_name = urllib.parse.quote(name)
    return f"https://scholar.google.com/citations?view_op=search_authors&mauthors={encoded_name}"


def manual_id_entry(name: str) -> Optional[str]:
    """
    Manually enter a Google Scholar ID with guidance.
    
    Args:
        name: Faculty name
        
    Returns:
        Scholar ID or None
    """
    search_url = get_search_url(name)
    
    print(f"\n  Manual search required for: {name}")
    print(f"  Search URL: {search_url}")
    print(f"\n  Instructions:")
    print(f"  1. Open the URL above in your browser")
    print(f"  2. Find the correct profile")
    print(f"  3. Click on it to open their profile page")
    print(f"  4. Copy the 'user=' value from the URL")
    print(f"     Example: https://scholar.google.com/citations?user=ABC123XYZ")
    print(f"              The scholar_id is: ABC123XYZ")
    
    while True:
        response = input(f"\n  Enter scholar_id (or 'skip' to skip, 'none' if no profile): ").strip()
        
        if response.lower() == 'skip':
            return None
        elif response.lower() == 'none':
            print(f"  ⊘ Marked as no profile")
            return None
        elif response:
            # Validate that it looks like a scholar ID
            if len(response) > 5 and not ' ' in response:
                # Show confirmation URL
                confirm_url = f"https://scholar.google.com/citations?user={response}"
                print(f"\n  Confirmation URL: {confirm_url}")
                confirm = input(f"  Is this correct? (y/n): ").strip().lower()
                if confirm == 'y':
                    return response
                else:
                    print(f"  Let's try again...")
            else:
                print(f"  That doesn't look like a valid scholar_id. Try again.")
        else:
            print(f"  Please enter a scholar_id or 'skip'")


def find_missing_ids(data: List[Dict[str, str]], csv_path: str, interactive: bool = True, 
                     use_automated: bool = True, request_delay: float = 2.0, keyword: str = '') -> List[Dict[str, str]]:
    """
    Find and fill in missing Google Scholar IDs.
    
    Args:
        data: List of faculty records
        csv_path: Path to CSV file for incremental saves
        interactive: Whether to interactively ask for user input
        use_automated: Whether to try automated search first
        request_delay: Delay in seconds between requests (default: 2.0 for polite scraping)
        keyword: Additional keyword for searches (e.g., institution name)
        
    Returns:
        Updated list of faculty records
    """
    updated_count = 0
    skipped_count = 0
    still_missing = []
    ambiguous_results = []  # Track ambiguous results: (name, [(url, scholar_name), ...])
    
    for i, faculty in enumerate(data):
        # Skip if scholar_id is already present
        if faculty.get('scholar_id', '').strip():
            continue
        
        name = faculty['name']
        print(f"\n{'='*70}")
        print(f"Searching for: {name} ({i+1}/{len(data)})")
        print(f"{'='*70}")
        
        results = []
        
        # Try automated search first if enabled
        if use_automated:
            # Try web search first (most reliable)
            if DDGS_AVAILABLE:
                search_msg = f"  Searching web for Google Scholar profile..."
                if keyword:
                    search_msg += f" (with keyword: '{keyword}')"
                print(search_msg)
                results = search_web_for_scholar(name, keyword=keyword)
                
                if results:
                    print(f"  ✓ Found {len(results)} result(s) via web search")
                else:
                    print(f"  ⚠ No web search results found")
            
            # If web search didn't work, try direct Scholar search
            if not results and SCHOLARLY_AVAILABLE:
                print(f"  Trying direct Google Scholar search...")
                results = search_scholar_direct(name)
                
                if results:
                    print(f"  ✓ Found {len(results)} result(s) via direct search")
                else:
                    print(f"  ⚠ No direct search results found")
        
        # If automated search found results
        if results:
            if len(results) == 1 and interactive:
                # Single result - ask for confirmation
                result = results[0]
                print(f"\n  Found 1 matching result:")
                print(f"  Name: {result['name']}")
                print(f"  Affiliation: {result.get('affiliation', 'N/A')}")
                if 'interests' in result:
                    print(f"  Interests: {result['interests']}")
                print(f"  URL: {result['url']}")
                
                # Check if it's an exact name match
                if names_match(name, result['name'], threshold=0.95):
                    response = input(f"\n  Accept this profile? (Y/n/skip/manual) [Y]: ").strip().lower()
                    if not response or response == 'y':
                        faculty['scholar_id'] = result['scholar_id']
                        updated_count += 1
                        save_faculty_data(csv_path, data)  # Save immediately
                        print(f"  ✓ Updated {name}")
                    elif response == 'skip':
                        skipped_count += 1
                        still_missing.append(name)
                        print(f"  ⊘ Skipped {name}")
                    elif response == 'manual':
                        print(f"  Switching to manual mode...")
                        scholar_id = manual_id_entry(name)
                        if scholar_id:
                            faculty['scholar_id'] = scholar_id
                            updated_count += 1
                            save_faculty_data(csv_path, data)  # Save immediately
                            print(f"  ✓ Updated {name}")
                        else:
                            skipped_count += 1
                            still_missing.append(name)
                    else:
                        print(f"  Switching to manual mode...")
                        scholar_id = manual_id_entry(name)
                        if scholar_id:
                            faculty['scholar_id'] = scholar_id
                            updated_count += 1
                            save_faculty_data(csv_path, data)  # Save immediately
                            print(f"  ✓ Updated {name}")
                        else:
                            skipped_count += 1
                            still_missing.append(name)
                else:
                    response = input(f"\n  Is this correct? (y/n/skip/manual): ").strip().lower()
                    
                    if response == 'y':
                        faculty['scholar_id'] = result['scholar_id']
                        updated_count += 1
                        save_faculty_data(csv_path, data)  # Save immediately
                        print(f"  ✓ Updated {name}")
                    elif response == 'skip':
                        skipped_count += 1
                        still_missing.append(name)
                        print(f"  ⊘ Skipped {name}")
                    elif response == 'manual':
                        print(f"  Switching to manual mode...")
                        scholar_id = manual_id_entry(name)
                        if scholar_id:
                            faculty['scholar_id'] = scholar_id
                            updated_count += 1
                            save_faculty_data(csv_path, data)  # Save immediately
                            print(f"  ✓ Updated {name}")
                        else:
                            skipped_count += 1
                            still_missing.append(name)
                    else:
                        print(f"  Switching to manual mode...")
                        scholar_id = manual_id_entry(name)
                        if scholar_id:
                            faculty['scholar_id'] = scholar_id
                            updated_count += 1
                            save_faculty_data(csv_path, data)  # Save immediately
                            print(f"  ✓ Updated {name}")
                        else:
                            skipped_count += 1
                            still_missing.append(name)
            
            elif len(results) > 1:
                # Multiple results - present options
                print(f"\n  Found {len(results)} matching profile(s):\n")
                
                # Store for ambiguous report
                url_list = [(r['url'], r['name']) for r in results]
                
                for idx, result in enumerate(results, 1):
                    print(f"  {idx}. {result['name']}")
                    print(f"     Affiliation: {result.get('affiliation', 'N/A')}")
                    if 'interests' in result:
                        print(f"     Interests: {result['interests']}")
                    print(f"     URL: {result['url']}")
                    print()
                
                if interactive:
                    while True:
                        response = input(f"  Select 1-{len(results)}, 'n' for none, 'manual' for manual entry, or 'skip': ").strip().lower()
                        
                        if response == 'n':
                            print(f"  ✗ Not updated")
                            skipped_count += 1
                            still_missing.append(name)
                            ambiguous_results.append((name, url_list))  # Track ambiguous
                            break
                        elif response == 'skip':
                            skipped_count += 1
                            still_missing.append(name)
                            ambiguous_results.append((name, url_list))  # Track ambiguous
                            print(f"  ⊘ Skipped {name}")
                            break
                        elif response == 'manual':
                            scholar_id = manual_id_entry(name)
                            if scholar_id:
                                faculty['scholar_id'] = scholar_id
                                updated_count += 1
                                save_faculty_data(csv_path, data)  # Save immediately
                                print(f"  ✓ Updated {name}")
                            else:
                                skipped_count += 1
                                still_missing.append(name)
                            break
                        elif response.isdigit():
                            choice = int(response)
                            if 1 <= choice <= len(results):
                                selected = results[choice - 1]
                                faculty['scholar_id'] = selected['scholar_id']
                                updated_count += 1
                                save_faculty_data(csv_path, data)  # Save immediately
                                print(f"  ✓ Updated {name} with scholar_id: {selected['scholar_id']}")
                                break
                            else:
                                print(f"  Invalid choice. Please select 1-{len(results)}")
                        else:
                            print(f"  Invalid input. Please enter a number, 'n', 'manual', or 'skip'")
                else:
                    # Non-interactive mode - skip ambiguous results
                    print(f"  ⚠ Multiple matches found (non-interactive mode) - skipping")
                    skipped_count += 1
                    still_missing.append(name)
                    ambiguous_results.append((name, url_list))  # Track ambiguous
            
            elif len(results) == 1 and not interactive:
                # Non-interactive with single result - auto-accept
                result = results[0]
                faculty['scholar_id'] = result['scholar_id']
                updated_count += 1
                save_faculty_data(csv_path, data)  # Save immediately
                print(f"  ✓ Auto-updated {name} with {result['name']}")
        
        # If no automated results, use manual mode
        elif interactive:
            scholar_id = manual_id_entry(name)
            if scholar_id:
                faculty['scholar_id'] = scholar_id
                updated_count += 1
                save_faculty_data(csv_path, data)  # Save immediately
                print(f"  ✓ Updated {name}")
            else:
                skipped_count += 1
                still_missing.append(name)
        else:
            # Non-interactive, no results
            skipped_count += 1
            still_missing.append(name)
        
        # Add delay between searches (polite scraping)
        if i < len(data) - 1 and use_automated:
            time.sleep(request_delay)
    
    print(f"\n{'='*70}")
    print(f"Summary:")
    print(f"  Updated: {updated_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"{'='*70}")
    
    # Report missing IDs
    if still_missing:
        print(f"\nFaculty still missing Google Scholar IDs ({len(still_missing)}):")
        for name in still_missing:
            print(f"  - {name}")
        print()
        # Report ambiguous results in tabular format
    if ambiguous_results:
        print(f"\nAmbiguous Results (Multiple Matches Found):")
        print(f"{'='*120}")
        print(f"{'Faculty Name':<40} | {'Scholar Profile Name':<40} | {'URL':<38}")
        print(f"{'-'*40}-+-{'-'*40}-+-{'-'*38}")
        for faculty_name, urls in ambiguous_results:
            for idx, (url, profile_name) in enumerate(urls):
                if idx == 0:
                    print(f"{faculty_name:<40} | {profile_name:<40} | {url:<38}")
                else:
                    print(f"{'':<40} | {profile_name:<40} | {url:<38}")
            print(f"{'-'*40}-+-{'-'*40}-+-{'-'*38}")
        print()
        return data


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Find missing Google Scholar identifiers for faculty members'
    )
    parser.add_argument(
        '--csv',
        default='faculty_scholar_data.csv',
        help='Path to the CSV file (default: faculty_scholar_data.csv)'
    )
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run in non-interactive mode (skip ambiguous results)'
    )
    parser.add_argument(
        '--manual-only',
        action='store_true',
        help='Skip automated search, use manual entry only'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=2.0,
        help='Delay between requests in seconds (default: 2.0 for polite scraping)'
    )
    parser.add_argument(
        '--keyword',
        type=str,
        default='',
        help='Additional keyword for searches (e.g., "Cornell" to find Cornell faculty)'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("Google Scholar ID Finder")
    print("="*70)
    
    # Check what search methods are available
    if not args.manual_only:
        if DDGS_AVAILABLE:
            print("\n✓ Web search enabled (via DuckDuckGo)")
        else:
            print("\n⚠ duckduckgo-search not available")
            print("  Install with: pip install duckduckgo-search")
        
        if SCHOLARLY_AVAILABLE:
            print("✓ Direct Google Scholar search available (may be blocked)")
        
        if not DDGS_AVAILABLE and not SCHOLARLY_AVAILABLE:
            print("\n⚠ No automated search available - switching to manual mode")
            args.manual_only = True
    else:
        print("\n📝 Manual-only mode enabled")
    
    print("\nLoading faculty data...")
    data = load_faculty_data(args.csv)
    
    print(f"Loaded {len(data)} faculty records")
    missing = sum(1 for f in data if not f.get('scholar_id', '').strip())
    print(f"Faculty without scholar_id: {missing}")
    
    if missing == 0:
        print("\n✓ All faculty members already have Google Scholar IDs!")
        return
    
    print("\nStarting search for missing Google Scholar IDs...")
    search_info = f"Using {args.delay}s delay between requests (DuckDuckGo recommends 1-2s for polite scraping)"
    if args.keyword:
        search_info += f"\nUsing keyword filter: '{args.keyword}'"
    print(search_info)
    print()
    
    # Find and fill missing IDs
    updated_data = find_missing_ids(
        data,
        csv_path=args.csv,
        interactive=not args.non_interactive,
        use_automated=not args.manual_only,
        request_delay=args.delay,
        keyword=args.keyword
    )
    
    # Final save to ensure all data is persisted
    save_faculty_data(args.csv, updated_data)
    
    print("\n✓ Done!")


if __name__ == '__main__':
    main()
