# Music Tracker

Advanced CLI tool for tracking and organizing DAW music projects across multiple stages: raw discovery → refined catalog → rejected.

## Features

- **Multi-DAW Support**: FL Studio (.flp), Logic Pro (.logicx), Studio One (.song), Bitwig (.bwproject)
- **Smart Project Detection**: Automatically detects project folders and uses appropriate titles
- **Three-Stage Organization**: Raw discovery → Refined catalog → Rejected archive
- **Duplicate Prevention**: Skips backup files and duplicate project titles
- **Interactive Review**: Easy workflow for processing projects at your own pace
- **Cross-Platform**: Works on macOS, Windows, and Linux
- **Metadata Tracking**: Genre, rating, tags, collaboration info, and more

## Installation

### Option 1: Install from Source

```bash
git clone <repository-url>
cd music_tracker
pip3 install --user .
```

### Option 2: Manual Installation

```bash
# Copy script to PATH
cp music_tracker/music_tracker.py ~/.local/bin/music-tracker
chmod +x ~/.local/bin/music-tracker

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Quick Start

```bash
# Add your project directories
music-tracker add "/path/to/FL Studio Projects"
music-tracker add "/path/to/Logic Projects"
music-tracker add "/path/to/Bitwig Projects"

# Check what was discovered
music-tracker stats

# Start reviewing projects interactively
music-tracker review

# List your refined collection
music-tracker refined
```

## Commands

### Discovery & Management

#### `add <directory>`
Scan directory for DAW projects and add to raw database.

```bash
music-tracker add "/Users/john/Music/Logic Projects"
music-tracker add "~/Documents/FL Studio"
```

**What it does:**
- Recursively scans for project files
- Skips backup files (auto-backup folders, timestamped files)
- Prevents duplicate titles
- Extracts basic metadata (size, dates, DAW type)

#### `stats`
Show database statistics and overview.

```bash
music-tracker stats
```

**Output:**
```
Music Tracker Statistics
========================================
Total discovered: 247
Refined songs: 89
Rejected: 34
Unprocessed: 124

DAW Breakdown (Refined):
   Logic Pro: 45
   Bitwig: 28
   FL Studio: 16
```

### Listing Projects

#### `list [--limit N] [--offset N] [--daw TYPE]`
List unprocessed raw projects.

```bash
music-tracker list                    # Show 20 recent projects
music-tracker list --limit 50        # Show 50 projects
music-tracker list --daw "Logic"     # Filter by DAW
music-tracker list --offset 20       # Skip first 20 (pagination)
```

#### `refined [--limit N] [--offset N] [--daw TYPE]`
List refined/curated projects.

```bash
music-tracker refined                 # Show refined collection
music-tracker refined --daw Bitwig   # Filter by DAW
```

**Output:**
```
Refined Projects (showing 10):
────────────────────────────────────────────────────────────────────────────────────────
ID:  15 | Logic Pro    | Summer Nights              | House        |  8/10 | complete
ID:  23 | Bitwig       | Acid Dreams                | Techno       |  9/10 | complete
ID:  31 | FL Studio    | Chill Vibes                | Ambient      |  7/10 | demo
```

### Project Details

#### `show <ID or title>`
Show detailed information about a project.

```bash
music-tracker show 15               # Show by ID
music-tracker show "Summer Nights" # Show by title (partial match)
```

**Output:**
```
Title: Summer Nights
Description: Uplifting house track with piano
Genre: House
Status: complete
Rating: 8/10
Tags: piano, uplifting, summer
DAW: Logic Pro
Path: /Users/john/Music/Logic/Summer Nights/Summer Nights.logicx
Size: 45.7 MB
Created: 2024-03-15
Refined: 2024-05-28
```

#### `open <ID or title>`
Open project with system default program.

```bash
music-tracker open 15               # Open by ID
music-tracker open "Summer"         # Open by partial title match
```

### Interactive Review

#### `review [--limit N]`
Interactive mode for processing raw projects.

```bash
music-tracker review               # Review 10 projects
music-tracker review --limit 5    # Review 5 projects
```

**Interactive options:**
- **[r]** - Refine: Add to refined database with metadata
- **[o]** - Open: Launch project in DAW to listen/evaluate
- **[x]** - Reject: Mark as not useful
- **[s]** - Skip: Leave for later
- **[q]** - Quit: Exit review mode

**Refinement prompts:**
```
Title [detected title]: My Amazing Track
Description: Energetic house track with vocal samples
Genre: House
Status [complete]: complete
Rating (1-10): 8
Tags (comma-separated): energetic, vocal, house
```

### Manual Operations

#### `refine <ID> [options]`
Manually refine a project with metadata.

```bash
music-tracker refine 15 \
  --title "Summer Nights" \
  --description "Uplifting house track" \
  --genre "House" \
  --rating 8 \
  --tags "piano,uplifting,summer" \
  --status "complete"
```

**Available options:**
- `--title` - Project title
- `--description` - Description
- `--genre` - Musical genre
- `--bpm` - Beats per minute
- `--key` - Key signature
- `--status` - Status (demo, complete, released, etc.)
- `--rating` - Rating 1-10
- `--tags` - Comma-separated tags
- `--collaboration` - Collaborator names

#### `reject <ID> [--reason "text"]`
Reject a project as not useful.

```bash
music-tracker reject 23 --reason "Just a test project"
music-tracker reject 45  # Uses default reason
```

### Information

#### `version`
Show version and database location.

```bash
music-tracker version
```

**Output:**
```
Music Tracker v1.1.0
Advanced CLI tool for tracking DAW music projects
Database location: /Users/john/Library/Application Support/MusicTracker/music_tracker.db
```

## Smart Project Detection

### Folder Structure Recognition

**FL Studio (.flp)**
- Usually standalone files
- Uses filename as title

**Logic Pro (.logicx)**
- Can be standalone packages or in project folders
- Uses folder name when in dedicated project folder

**Studio One (.song)**
- Always in project folders
- Uses folder name as title

**Bitwig (.bwproject)**
- Always in project folders  
- Uses folder name as title
- Skips versioned files (prefers main project file)

### Backup File Detection

Automatically skips:
- Files in `auto-backup`, `auto-save`, `backup` folders
- Files with timestamps: `project [2024-05-25 151417].bwproject`
- Files ending in `.bak`, `.tmp`, `~`

### Example Project Structure

```
My Projects/
├── FL Studio/
│   ├── Track1.flp              → "Track1"
│   └── Track2.flp              → "Track2"
├── Logic/
│   ├── Song A/
│   │   └── Song A.logicx       → "Song A"
│   └── Song B.logicx           → "Song B"  
└── Bitwig/
    └── Epic Song/
        ├── Epic Song.bwproject → "Epic Song"
        ├── auto-backups/      (skipped)
        ├── bounce/
        └── samples/
```

## Database Storage

**Default locations:**
- **macOS**: `~/Library/Application Support/MusicTracker/music_tracker.db`
- **Linux**: `~/.config/music-tracker/music_tracker.db`
- **Windows**: `~/AppData/Local/MusicTracker/music_tracker.db`

**Custom database:**
```bash
music-tracker --db /path/to/custom.db stats
```

## Workflow Examples

### Initial Setup

```bash
# Scan all your music directories
music-tracker add "/Users/john/Music/Logic Projects"
music-tracker add "/Users/john/Music/FL Studio"
music-tracker add "/Users/john/Documents/Bitwig Projects"

# See what was discovered
music-tracker stats
```

### Weekly Review Session

```bash
# Process 20 projects in interactive mode
music-tracker review --limit 20

# Check progress
music-tracker stats

# Browse your refined collection
music-tracker refined
```

### Finding Projects

```bash
# Find a specific project
music-tracker show "Summer"

# Open it in your DAW
music-tracker open "Summer Nights"

# List all house tracks
music-tracker refined | grep House
```

### Bulk Operations

```bash
# Mark multiple test projects as rejected
music-tracker reject 45 --reason "Test project"
music-tracker reject 67 --reason "Test project"

# Refine a completed track
music-tracker refine 89 \
  --title "Midnight Drive" \
  --genre "Synthwave" \
  --rating 9 \
  --status "released"
```

## Tips & Best Practices

### Organizing Your Projects

1. **Use consistent naming** - Good folder/file names become better titles
2. **Regular reviews** - Process projects shortly after creating them
3. **Use descriptive tags** - Makes searching easier later
4. **Rate everything** - Helps identify your best work

### Efficient Workflow

1. **Scan periodically** - Add new project directories as you create them
2. **Batch review** - Process 10-20 projects at once
3. **Use the open feature** - Listen to projects during review to make better decisions
4. **Tag consistently** - Develop a consistent tagging vocabulary

### Avoiding Issues

1. **Don't move projects** after adding - Paths will break
2. **Backup your database** - It's in your system's app data directory
3. **Use version control** for the database if it's important
4. **Regular stats checks** - Monitor your collection growth

## Troubleshooting

### Projects Not Found

```bash
# Check if paths are correct
music-tracker show 15

# If paths are broken, re-add the directory
music-tracker add "/new/path/to/projects"
```

### Database Issues

```bash
# Check database location
music-tracker version

# Start fresh if needed
rm ~/Library/Application\ Support/MusicTracker/music_tracker.db
music-tracker add "/path/to/projects"
```

### Installation Issues

```bash
# Ensure you're in PATH
which music-tracker

# Add to PATH if needed
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Short Alias

The tool installs with a short alias `mt` for faster access:

```bash
mt add "~/Music"
mt review
mt stats
mt show "My Track"
```

## Development

Built with Python 3.7+, uses SQLite for storage, and follows platform conventions for configuration files.

**Dependencies:**
- Python 3.7+
- SQLite3 (included with Python)
- pathlib, json, argparse (standard library)

