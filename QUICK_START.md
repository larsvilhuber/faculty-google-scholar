# Quick Start Guide: Finding Google Scholar IDs

## ✅ Good News: Automated Search Works!

The script now uses **web search** (via DuckDuckGo) to automatically find Google Scholar profiles. This is much more reliable than trying to access Google Scholar directly.

## How It Works

The script searches Google Scholar using `site:scholar.google.com/citations [Name]` and presents you with matching profiles to verify.

## Basic Usage

### Step 1: Run the script

```bash
source venv/bin/activate  # or: source .venv/bin/activate
python find_scholar_ids.py
```

### Step 2: Review and select profiles

For each faculty member, you'll see something like:

```
======================================================================
Searching for: Amanda Agan (1/51)
======================================================================
  Searching web for Google Scholar profile...
  ✓ Found 3 result(s) via web search

  Found 3 possible matches:

  1. Amanda Agan
     Affiliation: Cornell University · Verified email at cornell.edu
     URL: https://scholar.google.com/citations?user=jysM7c4AAAAJ

  2. Amanda Ang  
     Affiliation: Aalto University
     URL: https://scholar.google.com/citations?user=-6ydlRsAAAAJ

  3. A. Amanda
     Affiliation: Different University
     URL: https://scholar.google.com/citations?user=jVrmUosAAAAJ

  Select 1-3, 'n' for none, 'manual' for manual entry, or 'skip': 
```

### Step 3: Choose the correct profile

- Look for **Cornell affiliation** (or previous institutions if recently joined)
- Check that research interests match economics
- Enter the number of the correct profile (e.g., `1`)

Your options:
- **1-N**: Select that profile number
- **n**: None match (skip this person)
- **manual**: Enter scholar_id manually
- **skip**: Skip for now (will ask again next run)

### Step 4: The script updates automatically

```
  ✓ Updated Amanda Agan with scholar_id: jysM7c4AAAAJ
```

## Tips for Success

### What to Look For
1. **Affiliation**: Should show "Cornell" or a previous institution
2. **Research areas**: Should include economics-related keywords
3. **Publications**: Click the URL to verify if needed

### If You're Unsure
- Type **'skip'** to come back to them later
- Click the URL to open the profile in your browser and verify
- Look for verified email addresses (shows ✓)

### Common Situations

**Single match found:**
```
  Found 1 result:
  Name: Amanda Agan
  Affiliation: Cornell University
  URL: https://scholar.google.com/citations?user=jysM7c4AAAAJ

  Is this correct? (y/n/skip/manual): y
```

**No matches found:**
```
  ⚠ No web searchresults found

  Manual search required for: [Name]
  Search URL: https://scholar.google.com/citations?view_op=search_authors&mauthors=[Name]
  
  Enter scholar_id (or 'skip' to skip, 'none' if no profile):
```

## Manual Entry Mode

If automated search isn't working well, use manual mode:

```bash
python find_scholar_ids.py --manual-only
```

This provides search URLs for you to open in a browser, then you paste back the scholar_id.

## After Finding IDs

Once IDs are populated, update the citation metrics:

```bash
python update_citations.py
```

This fetches current citation counts and h-index values for all faculty with scholar IDs.

## Time Estimate

- **Automated mode**: ~1-2 minutes per faculty (includes search + verification)
- **For 51 faculty**: Approximately 1-2 hours total
- You can stop and resume anytime (progress is saved)

## Resume After Interruption

The script only processes faculty without scholar IDs, so you can:
1. Run the script
2. Process some faculty
3. Stop (Ctrl+C)
4. Run again later - it picks up where you left off

## Example Complete Session

```bash
$ source venv/bin/activate
$ python find_scholar_ids.py

Loaded 51 faculty records
Faculty without scholar_id: 51

[... processes each faculty member ...]

Summary:
  Updated: 45
  Skipped: 6

Data saved to faculty_scholar_data.csv
✓ Done!
```
