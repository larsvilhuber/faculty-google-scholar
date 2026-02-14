# Google Scholar Faculty Citation Tracker

A Python-based toolkit for tracking Google Scholar citations and h-index metrics for faculty members.

## Overview

This project provides tools to:
1. Extract faculty names from a Word document
2. Create and maintain a CSV database of faculty Google Scholar metrics
3. Find and add missing Google Scholar identifiers
4. Update citation counts and h-index values

## Project Structure

```
.
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── cornell-faculty-summaries.docx # Source document with faculty data
├── faculty_scholar_data.csv       # Output: Faculty metrics database
├── extract_faculty_data.py        # Script 1: Extract initial data
├── find_scholar_ids.py           # Script 2: Find Google Scholar IDs
└── update_citations.py           # Script 3: Update citation metrics
```

## Installation and Setup

### Step 1: Create Virtual Environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### 1. Extract Initial Faculty Data

This step extracts faculty names and existing Google Scholar metrics from the Word document.

```bash
python extract_faculty_data.py
```

**Output:** Creates `faculty_scholar_data.csv` with columns:
- `name`: Faculty member's full name
- `scholar_id`: Google Scholar identifier (initially empty)
- `citations`: Total citation count
- `h_index`: h-index value
- `as_of_date`: Date of last update

### 2. Find Missing Google Scholar IDs

This script uses web search (via DuckDuckGo) to automatically find Google Scholar profiles for faculty members.

**Recommended Approach (Automated with verification):**
```bash
python find_scholar_ids.py
```

**For better results (e.g., Cornell faculty):**
```bash
python find_scholar_ids.py --keyword "Cornell"
```

**How it works:**
1. The script searches `site:scholar.google.com/citations [Name]` for each faculty member
2. It presents you with matching Google Scholar profiles
3. You verify and select the correct one (look for Cornell affiliation, matching research areas)
4. The script updates the CSV with the scholar_id

**Example Interactive Session:**
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
     Affiliation: Politeknik Kesehatan
     URL: https://scholar.google.com/citations?user=jVrmUosAAAAJ

  Select 1-3, 'n' for none, 'manual' for manual entry, or 'skip': 1
  ✓ Updated Amanda Agan
```

**Options during interactive mode:**
- **Enter a number (1-N)**: Select that profile
- **'n'**: None of these are correct (skip this person)
- **'manual'**: Switch to manual entry mode (you provide the URL)
- **'skip'**: Skip this person for now (will ask again next time)

**Manual Mode (if automated search has issues):**
```bash
python find_scholar_ids.py --manual-only
```

This mode provides you with a search URL, you find the profile in your browser, and paste the scholar_id back into the script.

**Command-Line Options:**

| Option | Description |
|--------|-------------|
| `--csv FILE` | Specify CSV file (default: faculty_scholar_data.csv) |
| `--keyword WORD` | Add keyword to searches (e.g., "Cornell" for institution) |
| `--delay SECONDS` | Delay between requests (default: 2.0 seconds) |
| `--non-interactive` | Skip ambiguous results automatically |
| `--manual-only` | Skip automated search, manual entry only |

**Example with keyword:**
```bash
python find_scholar_ids.py --keyword "Cornell economics"
```

This searches for `site:scholar.google.com/citations [Name] Cornell economics`, which significantly improves accuracy by filtering to the institution.

**Ambiguous Results Report:**

At the end of the run, if multiple profiles were found for any faculty (and you skipped them), the script displays a table:

```
Ambiguous Results (Multiple Matches Found):
========================================================================================================================
Faculty Name                             | Scholar Profile Name                     | URL
-----------------------------------------+------------------------------------------+----------------------------------------
John Smith                               | John Smith                               | https://scholar.google.com/.../user1  
                                         | John M. Smith                            | https://scholar.google.com/.../user2  
                                         | J. Smith                                 | https://scholar.google.com/.../user3  
-----------------------------------------+------------------------------------------+----------------------------------------
```

This helps you review and manually investigate ambiguous cases later.

### 3. Update Citation Metrics

This script updates citations and h-index for all faculty with Google Scholar IDs.

```bash
python update_citations.py
```

**Features:**
- **Incremental updates**: Saves CSV after each successful update (safe to interrupt and restart)
- **Smart skipping**: Automatically skips entries updated within the last 7 days
- **Rate limiting**: 30-second delay between requests to avoid Google Scholar blocks
- Records the update date in `as_of_date`
- Shows before/after values for each faculty member

**Command-Line Options:**

| Option | Description |
|--------|-------------|
| `--csv FILE` | Specify CSV file (default: faculty_scholar_data.csv) |
| `--query-delay SECONDS` | Delay between requests (default: 30.0 seconds) |
| `--update-delay-days DAYS` | Skip entries updated within N days (default: 7) |
| `--stats-only` | Show statistics only, without updating |

**Examples:**

Show statistics only (no updates):
```bash
python update_citations.py --stats-only
```

Update all entries regardless of when last updated:
```bash
python update_citations.py --update-delay-days 0
```

Use faster delay (not recommended, may cause rate limiting):
```bash
python update_citations.py --query-delay 15
```

Custom CSV file with conservative delay:
```bash
python update_citations.py --csv my_data.csv --query-delay 60
```

**How Smart Skipping Works:**

By default, the script only updates entries that haven't been updated in the last 7 days. This allows you to:
- Run the script multiple times without waiting
- Resume after being rate-limited by Google Scholar
- Update only stale data without wasting time

The script will tell you which entries are being skipped:
```
Will update 10 faculty members (out of 45 with Google Scholar IDs)
Skipping 35 recently updated (within 7 days)
```

## Data Format

### CSV Schema

The `faculty_scholar_data.csv` file contains the following columns:

| Column       | Type   | Description                                    |
|-------------|--------|------------------------------------------------|
| name        | string | Full name of faculty member                   |
| scholar_id  | string | Google Scholar author ID                       |
| citations   | int    | Total citation count                           |
| h_index     | int    | h-index value                                  |
| as_of_date  | date   | Date of last update (YYYY-MM-DD format)       |

### Example Row

```csv
name,scholar_id,citations,h_index,as_of_date
Amanda Agan,abc123def,2163,16,2025-11-15
```

## Statistics Output

The `update_citations.py` script provides comprehensive statistics about your dataset, including measures of central tendency and distribution. Use `--stats-only` to view statistics without updating data.

### Dataset Overview
- Total faculty count
- Number with Google Scholar IDs  
- Number with citation data

### Citation Statistics
- **Total citations**: Sum of all citations across faculty
- **Average citations**: Mean citation count
- **Median citations**: Middle value (useful for skewed distributions)
- **Max/Min citations**: Range of citation counts

### H-Index Statistics
- **Average h-index**: Mean h-index value
- **Median h-index**: Middle value (often more representative than mean)
- **Max/Min h-index**: Range of h-index values

**Example output:**
```
Citation Statistics:
  Total citations: 337,750
  Average citations: 7,506
  Median citations: 2,626
  Max citations: 38,813
  Min citations: 19

H-Index Statistics:
  Average h-index: 24.9
  Median h-index: 19
  Max h-index: 91
  Min h-index: 2
```

**Note:** Median values are particularly useful for academic metrics, which often have skewed distributions due to highly-cited researchers. The median represents the "typical" faculty member better than the average when outliers are present.

## Workflow

### Initial Setup (One-time)
1. Place faculty Word document in project directory
2. Create virtual environment and install dependencies
3. Run `extract_faculty_data.py` to create initial CSV
4. Run `find_scholar_ids.py` to populate Google Scholar IDs

### Regular Updates (Periodic)
1. Activate virtual environment
2. Run `update_citations.py` to refresh metrics
3. Database is automatically updated with new citation counts

### Adding New Faculty
1. Update the Word document with new faculty information
2. Re-run `extract_faculty_data.py` (backs up existing IDs)
3. Run `find_scholar_ids.py` to find IDs for new faculty
4. Run `update_citations.py` to get current metrics

## Important Notes

### Rate Limiting
Google Scholar may block requests if too many are made too quickly. The scripts include:
- Default 1-second delay between requests
- Use `--delay` to increase if needed
- Consider using the `scholarly` library's proxy features for large updates

### Google Scholar IDs
- Scholar IDs are permanent identifiers (e.g., "abc123def")
- URLs format: `https://scholar.google.com/citations?user=SCHOLAR_ID`
- Once found, IDs don't need to be re-searched

### Best Practices
1. **Version Control**: Commit the CSV after each update cycle
2. **Backup**: Keep backups before major updates
3. **Regular Updates**: Run monthly or quarterly for trend tracking
4. **Verification**: Spot-check a few profiles after updates
5. **Log Maintenance**: The scripts output detailed logs - save for troubleshooting

## Troubleshooting

### Automated search not finding results

**Symptom:** The `find_scholar_ids.py` script reports "No automated results found" even for faculty with known profiles.

**Cause:** Google Scholar blocks automated access to prevent scraping.

**Solutions:**
1. **Use manual mode (RECOMMENDED):**
   ```bash
   python find_scholar_ids.py --manual-only
   ```
   This lets you search manually in a browser and paste the scholar_id.

2. **Wait and retry:** Google Scholar blocks are often temporary (24-48 hours)

3. **Use a different network:** Try from a different IP address or network

4. **Install proxy support:** The script tries to use free proxies, but these can be unreliable

### "No results found" for a faculty member
- Verify the exact name spelling in the CSV
- Check if they have a Google Scholar profile (search manually)
- Try searching with alternative name formats (e.g., with/without middle initial)
- Some faculty may not have public profiles or may use different name variations

### Rate limiting / Too many requests
- Increase delay: `--delay 2.0` or higher (in update_citations.py)
- Use `--manual-only` mode for finding IDs
- Run updates in smaller batches
- Wait 24 hours before retrying automated searches
- Automated blocking is common - manual mode is more reliable

### Import errors
- Ensure virtual environment is activated
- Re-run: `pip install -r requirements.txt`
- Check Python version (requires 3.7+)

### CSV encoding issues
- Files use UTF-8 encoding
- Open with compatible editors (VS Code, Excel with import settings)

## Advanced Usage

### Batch Processing
For large departments, update in batches to avoid rate limiting:

```python
# Modify update_citations.py to process specific rows
# or split CSV into smaller files
```

### Automated Scheduling
Set up a cron job (Linux/Mac) or Task Scheduler (Windows) to run updates automatically:

```bash
# Example cron: Update every month on the 1st at 2 AM
0 2 1 * * cd /path/to/project && source venv/bin/activate && python update_citations.py
```

### Export to Other Formats
```bash
# Convert CSV to Excel (requires pandas and openpyxl)
pip install pandas openpyxl
python -c "import pandas as pd; pd.read_csv('faculty_scholar_data.csv').to_excel('faculty_data.xlsx', index=False)"
```

## Dependencies

- **python-docx**: Reading Microsoft Word documents
- **scholarly**: Accessing Google Scholar profiles and metrics

## License

This project is for academic/research use. Please respect Google Scholar's Terms of Service and rate limits.

## Contact

For questions or issues, please contact the project maintainer.

## Changelog

### Version 1.0 (Initial Release)
- Extract faculty data from Word documents
- Interactive Google Scholar ID finder
- Automated citation metric updates
- CSV database management
