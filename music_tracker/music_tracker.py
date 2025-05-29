"""
Advanced Music Project Tracker CLI Tool
Tracks DAW projects across multiple stages: raw discovery -> refined catalog -> rejected

Version: 1.1.0
"""

import sqlite3
import os
import argparse
import json
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import sys

__version__ = "1.1.0"

class MusicTracker:
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use platform-appropriate config directory
            if platform.system() == "Darwin":  # macOS
                config_dir = Path.home() / "Library" / "Application Support" / "MusicTracker"
            elif platform.system() == "Windows":
                config_dir = Path.home() / "AppData" / "Local" / "MusicTracker"
            else:  # Linux
                config_dir = Path.home() / ".config" / "music-tracker"
            
            # Create directory if it doesn't exist
            config_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(config_dir / "music_tracker.db")
        else:
            self.db_path = db_path
            
        self.setup_database()
    
    def setup_database(self):
        """Initialize all three database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Raw projects table - unprocessed discoveries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_projects (
                id INTEGER PRIMARY KEY,
                project_file_path TEXT UNIQUE NOT NULL,
                project_folder_path TEXT,
                daw_type TEXT NOT NULL,
                detected_title TEXT NOT NULL,
                file_size_mb REAL,
                date_created DATE,
                date_modified DATE,
                date_discovered DATE DEFAULT CURRENT_DATE,
                additional_files TEXT,  -- JSON array of related files
                notes TEXT
            )
        ''')
        
        # Refined projects table - curated music collection
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refined_projects (
                id INTEGER PRIMARY KEY,
                raw_project_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                genre TEXT,
                bpm INTEGER,
                key_signature TEXT,
                year INTEGER,
                status TEXT DEFAULT 'complete',  -- demo, complete, released, etc
                rating INTEGER CHECK(rating >= 1 AND rating <= 10),
                tags TEXT,  -- JSON array
                collaboration TEXT,
                project_file_path TEXT NOT NULL,
                project_folder_path TEXT,
                daw_type TEXT NOT NULL,
                file_size_mb REAL,
                date_created DATE,
                date_refined DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (raw_project_id) REFERENCES raw_projects (id)
            )
        ''')
        
        # Rejected projects table - stuff that's not worth keeping
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rejected_projects (
                id INTEGER PRIMARY KEY,
                raw_project_id INTEGER,
                reason TEXT,
                project_file_path TEXT NOT NULL,
                detected_title TEXT,
                daw_type TEXT,
                date_rejected DATE DEFAULT CURRENT_DATE,
                FOREIGN KEY (raw_project_id) REFERENCES raw_projects (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def detect_daw_projects(self, directory: str) -> List[Dict]:
        """Scan directory for DAW project files and return project info"""
        projects = []
        directory_path = Path(directory)
        
        if not directory_path.exists():
            print(f"❌ Directory not found: {directory}")
            return projects
        
        # Define DAW project patterns
        daw_patterns = {
            '.flp': 'FL Studio',
            '.logicx': 'Logic Pro',
            '.song': 'Studio One',
            '.bwproject': 'Bitwig'
        }
        
        print(f"Scanning {directory} for DAW projects...")
        
        for pattern, daw_name in daw_patterns.items():
            for project_file in directory_path.rglob(f"*{pattern}"):
                # Skip backup files and temporary files
                if self._should_skip_file(project_file):
                    continue
                    
                project_info = self._analyze_project_file(project_file, daw_name, pattern)
                if project_info:
                    projects.append(project_info)
        
        return projects
    
    def _should_skip_file(self, project_file: Path) -> bool:
        """Check if we should skip this project file (backups, temps, etc.)"""
        file_path_str = str(project_file).lower()
        
        # Skip common backup/temp directories
        skip_patterns = [
            'auto-backup',
            'auto-save',
            'backup',
            'temp',
            'tmp',
            '.backup',
            '_backup',
            'autosave',
            'recovery'
        ]
        
        # Check if any parent directory matches backup patterns
        for part in project_file.parts:
            if any(pattern in part.lower() for pattern in skip_patterns):
                return True
        
        # Skip files with backup-like patterns in filename
        filename = project_file.name.lower()
        backup_filename_patterns = [
            ' [20',  # Bitwig backup format: "project [2024-05-25 151417].bwproject"
            '.bak',
            '_bak',
            '.backup',
            '_backup',
            '~',
            '.tmp'
        ]
        
        if any(pattern in filename for pattern in backup_filename_patterns):
            return True
        
        return False
    
    def _analyze_project_file(self, project_file: Path, daw_name: str, extension: str) -> Optional[Dict]:
        """Analyze individual project file and determine title/folder structure"""
        try:
            file_stat = project_file.stat()
            file_size_mb = file_stat.st_size / (1024 * 1024)
            
            # On macOS, get the actual creation time using birthtime
            try:
                if hasattr(file_stat, 'st_birthtime'):
                    # macOS/BSD - use birth time (actual creation time)
                    date_created = datetime.fromtimestamp(file_stat.st_birthtime).date()
                else:
                    # Linux/Windows fallback
                    date_created = datetime.fromtimestamp(file_stat.st_ctime).date()
            except (OSError, ValueError):
                # Fallback if birthtime fails
                date_created = datetime.fromtimestamp(file_stat.st_ctime).date()
            
            date_modified = datetime.fromtimestamp(file_stat.st_mtime).date()
            
            project_folder = None
            detected_title = project_file.stem
            
            # Determine if project is in a dedicated folder
            if extension in ['.song', '.bwproject']:
                # These are always in project folders
                project_folder = project_file.parent
                # Use folder name as title
                detected_title = project_folder.name
            
            elif extension == '.logicx':
                # Logic projects might be in folders or standalone packages
                parent_dir = project_file.parent
                # If parent folder name suggests it's a project folder
                if (parent_dir.name == project_file.stem or
                    any(sibling.name.startswith(project_file.stem) for sibling in parent_dir.iterdir() if sibling != project_file)):
                    project_folder = parent_dir
                    detected_title = parent_dir.name
            
            # FLP files are usually standalone, no special folder logic needed
            
            # Find additional files in project folder
            additional_files = []
            if project_folder:
                for item in project_folder.iterdir():
                    if item != project_file and item.is_file() and not item.name.startswith('.'):
                        additional_files.append(item.name)
            
            return {
                'project_file_path': str(project_file),
                'project_folder_path': str(project_folder) if project_folder else None,
                'daw_type': daw_name,
                'detected_title': detected_title,
                'file_size_mb': round(file_size_mb, 2),
                'date_created': date_created,
                'date_modified': date_modified,
                'additional_files': json.dumps(additional_files) if additional_files else None
            }
            
        except Exception as e:
            print(f"Error analyzing {project_file}: {e}")
            return None
    
    def add_directory(self, directory: str) -> int:
        """Scan directory and add all found projects to raw database"""
        projects = self.detect_daw_projects(directory)
        
        if not projects:
            print(f"No DAW projects found in {directory}")
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        added_count = 0
        
        for project in projects:
            try:
                cursor.execute('''
                    INSERT INTO raw_projects 
                    (project_file_path, project_folder_path, daw_type, detected_title, 
                     file_size_mb, date_created, date_modified, additional_files)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project['project_file_path'],
                    project['project_folder_path'],
                    project['daw_type'],
                    project['detected_title'],
                    project['file_size_mb'],
                    project['date_created'],
                    project['date_modified'],
                    project['additional_files']
                ))
                added_count += 1
                print(f"Added {project['daw_type']}: {project['detected_title']}")
                
            except sqlite3.IntegrityError:
                print(f"Already exists: {project['detected_title']}")
        
        conn.commit()
        conn.close()
        
        print(f"\nAdded {added_count} new projects to raw database")
        return added_count
    
    def list_refined_projects(self, limit: int = 20, offset: int = 0, daw_filter: str = None) -> List[Dict]:
        """List refined/curated projects"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, title, genre, status, rating, daw_type, file_size_mb, date_created, date_refined
            FROM refined_projects 
            WHERE 1=1
        '''
        params = []
        
        if daw_filter:
            query += ' AND daw_type LIKE ?'
            params.append(f'%{daw_filter}%')
        
        query += ' ORDER BY date_refined DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [dict(zip(['id', 'title', 'genre', 'status', 'rating', 'daw', 'size_mb', 'created', 'refined'], row)) for row in results]
        """List unprocessed raw projects"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT id, detected_title, daw_type, file_size_mb, date_created, project_file_path
            FROM raw_projects 
            WHERE id NOT IN (SELECT raw_project_id FROM refined_projects WHERE raw_project_id IS NOT NULL)
            AND id NOT IN (SELECT raw_project_id FROM rejected_projects WHERE raw_project_id IS NOT NULL)
        '''
        params = []
        
        if daw_filter:
            query += ' AND daw_type LIKE ?'
            params.append(f'%{daw_filter}%')
        
        query += ' ORDER BY date_discovered DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        conn.close()
        
        return [dict(zip(['id', 'title', 'daw', 'size_mb', 'created', 'path'], row)) for row in results]
    
    def show_project_details(self, identifier) -> Optional[Dict]:
        """Show detailed information about a project by ID or title"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Try to find by ID first (if it's a number)
        if str(identifier).isdigit():
            raw_id = int(identifier)
            cursor.execute('SELECT * FROM raw_projects WHERE id = ?', (raw_id,))
            result = cursor.fetchone()
            
            if result:
                columns = [desc[0] for desc in cursor.description]
                project_data = dict(zip(columns, result))
                project_data['source_table'] = 'raw'
            else:
                # Try refined projects by ID
                cursor.execute('SELECT * FROM refined_projects WHERE id = ?', (raw_id,))
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    project_data = dict(zip(columns, result))
                    project_data['source_table'] = 'refined'
                else:
                    conn.close()
                    return None
        else:
            # Search by title in both tables
            title_pattern = f"%{identifier}%"
            
            # Try raw projects first
            cursor.execute('SELECT * FROM raw_projects WHERE detected_title LIKE ? ORDER BY date_discovered DESC LIMIT 1', (title_pattern,))
            result = cursor.fetchone()
            
            if result:
                columns = [desc[0] for desc in cursor.description]
                project_data = dict(zip(columns, result))
                project_data['source_table'] = 'raw'
            else:
                # Try refined projects
                cursor.execute('SELECT * FROM refined_projects WHERE title LIKE ? ORDER BY date_refined DESC LIMIT 1', (title_pattern,))
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    project_data = dict(zip(columns, result))
                    project_data['source_table'] = 'refined'
                else:
                    conn.close()
                    return None
        
        conn.close()
        
        # Parse additional files if present
        if 'additional_files' in project_data and project_data['additional_files']:
            project_data['additional_files'] = json.loads(project_data['additional_files'])
        
        return project_data
    
    def run_analytics(self):
        """Run analytics module"""
        try:
            from . import music_analytics
            analytics = music_analytics.MusicAnalytics(self.db_path)
            analytics.generate_report()
        except ImportError:
            print("Analytics dependencies not installed!")
            print("Install with: pip install pandas matplotlib seaborn plotly numpy")
        except Exception as e:
            print(f"Error running analytics: {e}")
    
    def refine_project(self, raw_id: int, **metadata) -> bool:
        """Move project from raw to refined with additional metadata"""
        # Get raw project data
        raw_project = self.show_project_details(raw_id)
        if not raw_project:
            print(f"Raw project {raw_id} not found")
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Extract year from date_created if not provided
            year = metadata.get('year')
            if not year and raw_project['date_created']:
                year = int(raw_project['date_created'][:4])
            
            # Convert tags to JSON if provided as list
            tags = metadata.get('tags')
            if isinstance(tags, list):
                tags = json.dumps(tags)
            
            cursor.execute('''
                INSERT INTO refined_projects
                (raw_project_id, title, description, genre, bpm, key_signature, year, 
                 status, rating, tags, collaboration, project_file_path, project_folder_path,
                 daw_type, file_size_mb, date_created)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                raw_id,
                metadata.get('title', raw_project['detected_title']),
                metadata.get('description'),
                metadata.get('genre'),
                metadata.get('bpm'),
                metadata.get('key_signature'),
                year,
                metadata.get('status', 'complete'),
                metadata.get('rating'),
                tags,
                metadata.get('collaboration'),
                raw_project['project_file_path'],
                raw_project['project_folder_path'],
                raw_project['daw_type'],
                raw_project['file_size_mb'],
                raw_project['date_created']
            ))
            
            conn.commit()
            conn.close()
            print(f"Refined project: {metadata.get('title', raw_project['detected_title'])}")
            return True
            
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error refining project: {e}")
            return False
    
    def open_project(self, identifier) -> bool:
        """Open project file with system default program"""
        project_details = self.show_project_details(identifier)
        if not project_details:
            print(f"Project {identifier} not found")
            return False
        
        # Get the correct title field based on source table
        title = project_details.get('title') or project_details.get('detected_title')
        project_path = project_details['project_file_path']
        
        if not os.path.exists(project_path):
            print(f"Project file not found: {project_path}")
            return False
        
        try:
            print(f"Opening {title} with default program...")
            
            # Cross-platform file opening
            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", project_path], check=True)
            elif system == "Windows":
                os.startfile(project_path)
            else:  # Linux
                subprocess.run(["xdg-open", project_path], check=True)
            
            print(f"Opened: {project_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to open project: {e}")
            return False
        except Exception as e:
            print(f"Error opening project: {e}")
            return False
        """Move project to rejected database"""
        raw_project = self.show_project_details(raw_id)
        if not raw_project:
            print(f"Raw project {raw_id} not found")
            return False
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO rejected_projects
                (raw_project_id, reason, project_file_path, detected_title, daw_type)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                raw_id, reason, raw_project['project_file_path'],
                raw_project['detected_title'], raw_project['daw_type']
            ))
            
            conn.commit()
            conn.close()
            print(f"Rejected: {raw_project['detected_title']} - {reason}")
            return True
            
        except Exception as e:
            conn.rollback()
            conn.close()
            print(f"Error rejecting project: {e}")
            return False
    
    def interactive_review(self, limit: int = 10):
        """Interactive mode for reviewing raw projects"""
        raw_projects = self.list_raw_projects(limit=limit)
        
        if not raw_projects:
            print("No unprocessed projects found!")
            return
        
        print(f"\nFound {len(raw_projects)} unprocessed projects\n")
        
        for i, project in enumerate(raw_projects, 1):
            print(f"{'='*60}")
            print(f"Project {i}/{len(raw_projects)} (ID: {project['id']})")
            print(f"{'='*60}")
            
            # Show detailed info
            details = self.show_project_details(project['id'])
            self._display_project_details(details)
            
            while True:
                print("\nOptions:")
                print("  [r] - Refine (add to refined database)")
                print("  [o] - Open project file")
                print("  [x] - Reject (mark as useless)")
                print("  [s] - Skip for now")
                print("  [q] - Quit interactive mode")
                
                choice = input("\nChoice: ").strip().lower()
                
                if choice == 'r':
                    self._interactive_refine(project['id'])
                    break
                elif choice == 'o':
                    self.open_project(project['id'])
                    # Don't break - let user continue with other options after opening
                    print(f"\n{'='*60}")
                    print(f"Project {i}/{len(raw_projects)} (ID: {project['id']}) - Still reviewing")
                    print(f"{'='*60}")
                    self._display_project_details(details)
                elif choice == 'x':
                    reason = input("Reason for rejection (optional): ").strip() or "Not useful"
                    self.reject_project(project['id'], reason)
                    break
                elif choice == 's':
                    print("Skipped")
                    break
                elif choice == 'q':
                    print("Exiting interactive mode")
                    return
                else:
                    print("Invalid choice, please try again")
            
            print()
    
    def _display_project_details(self, details: Dict):
        """Display formatted project details"""
        if details['source_table'] == 'raw':
            print(f"Title: {details['detected_title']}")
            print(f"DAW: {details['daw_type']}")
            print(f"Path: {details['project_file_path']}")
            if details.get('project_folder_path'):
                print(f"Folder: {details['project_folder_path']}")
            print(f"Size: {details['file_size_mb']} MB")
            print(f"Created: {details['date_created']}")
            print(f"Modified: {details['date_modified']}")
            
            if details.get('additional_files'):
                print(f"Additional files: {', '.join(details['additional_files'][:3])}")
                if len(details['additional_files']) > 3:
                    print(f"    ... and {len(details['additional_files']) - 3} more")
        else:
            # Refined project
            print(f"Title: {details['title']}")
            print(f"Description: {details.get('description', 'N/A')}")
            print(f"Genre: {details.get('genre', 'N/A')}")
            print(f"Status: {details.get('status', 'N/A')}")
            if details.get('rating'):
                print(f"Rating: {details['rating']}/10")
            if details.get('bpm'):
                print(f"BPM: {details['bpm']}")
            if details.get('key_signature'):
                print(f"Key: {details['key_signature']}")
            if details.get('tags'):
                tags = json.loads(details['tags']) if isinstance(details['tags'], str) else details['tags']
                print(f"Tags: {', '.join(tags)}")
            if details.get('collaboration'):
                print(f"Collaboration: {details['collaboration']}")
            print(f"DAW: {details['daw_type']}")
            print(f"Path: {details['project_file_path']}")
            print(f"Size: {details['file_size_mb']} MB")
            print(f"Created: {details['date_created']}")
            print(f"Refined: {details['date_refined']}")
    
    def _interactive_refine(self, raw_id: int):
        """Interactive refinement process"""
        raw_project = self.show_project_details(raw_id)
        
        print(f"\nRefining: {raw_project['detected_title']}")
        
        metadata = {}
        
        # Title
        title = input(f"Title [{raw_project['detected_title']}]: ").strip()
        if title:
            metadata['title'] = title
        
        # Description
        description = input("Description: ").strip()
        if description:
            metadata['description'] = description
        
        # Genre
        genre = input("Genre: ").strip()
        if genre:
            metadata['genre'] = genre
        
        # Status
        status = input("Status [complete]: ").strip() or "complete"
        metadata['status'] = status
        
        # Rating
        rating_input = input("Rating (1-10): ").strip()
        if rating_input.isdigit() and 1 <= int(rating_input) <= 10:
            metadata['rating'] = int(rating_input)
        
        # Tags
        tags_input = input("Tags (comma-separated): ").strip()
        if tags_input:
            metadata['tags'] = [tag.strip() for tag in tags_input.split(',')]
        
        self.refine_project(raw_id, **metadata)
    
    def stats(self):
        """Show database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Raw projects count
        cursor.execute('SELECT COUNT(*) FROM raw_projects')
        raw_total = cursor.fetchone()[0]
        
        # Refined projects count
        cursor.execute('SELECT COUNT(*) FROM refined_projects')
        refined_total = cursor.fetchone()[0]
        
        # Rejected projects count
        cursor.execute('SELECT COUNT(*) FROM rejected_projects')
        rejected_total = cursor.fetchone()[0]
        
        # Unprocessed count
        cursor.execute('''
            SELECT COUNT(*) FROM raw_projects 
            WHERE id NOT IN (SELECT raw_project_id FROM refined_projects WHERE raw_project_id IS NOT NULL)
            AND id NOT IN (SELECT raw_project_id FROM rejected_projects WHERE raw_project_id IS NOT NULL)
        ''')
        unprocessed = cursor.fetchone()[0]
        
        # DAW breakdown
        cursor.execute('SELECT daw_type, COUNT(*) FROM refined_projects GROUP BY daw_type')
        daw_stats = cursor.fetchall()
        
        conn.close()
        
        print("\nMusic Tracker Statistics")
        print("=" * 40)
        print(f"Total discovered: {raw_total}")
        print(f"Refined songs: {refined_total}")
        print(f"Rejected: {rejected_total}")
        print(f"Unprocessed: {unprocessed}")
        
        if daw_stats:
            print(f"\nDAW Breakdown (Refined):")
            for daw, count in daw_stats:
                print(f"   {daw}: {count}")


def main():
    parser = argparse.ArgumentParser(description="Advanced Music Project Tracker")
    parser.add_argument('--db', help='Custom database file path (default: platform config directory)')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add directory command
    add_parser = subparsers.add_parser('add', help='Add directory to scan for projects')
    add_parser.add_argument('directory', help='Directory path to scan')
    
    # List raw projects command
    list_parser = subparsers.add_parser('list', help='List unprocessed raw projects')
    list_parser.add_argument('--limit', type=int, default=20, help='Number of projects to show')
    list_parser.add_argument('--offset', type=int, default=0, help='Offset for pagination')
    list_parser.add_argument('--daw', help='Filter by DAW type')
    
    # Show project details command
    show_parser = subparsers.add_parser('show', help='Show detailed info for a project')
    show_parser.add_argument('id', type=int, help='Raw project ID')
    
    # Interactive review command
    review_parser = subparsers.add_parser('review', help='Interactive review of raw projects')
    review_parser.add_argument('--limit', type=int, default=10, help='Number of projects to review')
    
    # Open project command
    open_parser = subparsers.add_parser('open', help='Open project with default program')
    open_parser.add_argument('id', type=int, help='Raw project ID')
    
    # Refine project command
    refine_parser = subparsers.add_parser('refine', help='Manually refine a project')
    refine_parser.add_argument('id', type=int, help='Raw project ID')
    refine_parser.add_argument('--title', help='Project title')
    refine_parser.add_argument('--description', help='Project description')
    refine_parser.add_argument('--genre', help='Musical genre')
    refine_parser.add_argument('--bpm', type=int, help='Beats per minute')
    refine_parser.add_argument('--key', help='Key signature')
    refine_parser.add_argument('--status', default='complete', help='Project status')
    refine_parser.add_argument('--rating', type=int, help='Rating 1-10')
    refine_parser.add_argument('--tags', help='Comma-separated tags')
    
    # Reject project command
    reject_parser = subparsers.add_parser('reject', help='Reject a project')
    reject_parser.add_argument('id', type=int, help='Raw project ID')
    reject_parser.add_argument('--reason', default='Not useful', help='Rejection reason')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    # Version command
    subparsers.add_parser('version', help='Show version information')
    
    # Analytics command
    subparsers.add_parser('analytics', help='Run analytics and generate visualizations')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    tracker = MusicTracker(args.db)
    
    if args.command == 'add':
        tracker.add_directory(args.directory)
    
    elif args.command == 'list':
        projects = tracker.list_raw_projects(args.limit, args.offset, args.daw)
        if projects:
            print(f"\nUnprocessed Projects (showing {len(projects)}):")
            print("-" * 80)
            for p in projects:
                print(f"ID: {p['id']:3d} | {p['daw']:12s} | {p['title'][:40]:40s} | {p['size_mb']:6.1f}MB")
        else:
            print("No unprocessed projects found")
    
    elif args.command == 'show':
        details = tracker.show_project_details(args.id)
        if details:
            tracker._display_project_details(details)
        else:
            print(f"Project {args.id} not found")
    
    elif args.command == 'review':
        tracker.interactive_review(args.limit)
    
    elif args.command == 'open':
        tracker.open_project(args.id)
    
    elif args.command == 'refine':
        metadata = {}
        if args.title: metadata['title'] = args.title
        if args.description: metadata['description'] = args.description
        if args.genre: metadata['genre'] = args.genre
        if args.bpm: metadata['bpm'] = args.bpm
        if args.key: metadata['key_signature'] = args.key
        if args.status: metadata['status'] = args.status
        if args.rating: metadata['rating'] = args.rating
        if args.tags: metadata['tags'] = [t.strip() for t in args.tags.split(',')]
        
        tracker.refine_project(args.id, **metadata)
    
    elif args.command == 'reject':
        tracker.reject_project(args.id, args.reason)
    
    elif args.command == 'stats':
        tracker.stats()
    
    elif args.command == 'version':
        print(f"Music Tracker v{__version__}")
        print("Advanced CLI tool for tracking DAW music projects")
        print(f"Database location: {tracker.db_path}")
    
    elif args.command == 'analytics':
        tracker.run_analytics()


if __name__ == '__main__':
    main()
