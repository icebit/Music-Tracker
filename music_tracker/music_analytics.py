#!/usr/bin/env python3
"""
Music Tracker Analytics Module
Advanced analysis and visualization of music project data
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from collections import Counter
import json

class MusicAnalytics:
    def __init__(self, db_path):
        self.db_path = db_path
        self.setup_style()
    
    def setup_style(self):
        """Set up plotting style"""
        plt.style.use('dark_background')
        sns.set_palette("husl")
    
    def load_data(self):
        """Load data from database into pandas DataFrames"""
        conn = sqlite3.connect(self.db_path)
        
        self.raw_df = pd.read_sql_query('''
            SELECT *, 'raw' as source FROM raw_projects
        ''', conn)
        
        self.refined_df = pd.read_sql_query('''
            SELECT *, 'refined' as source FROM refined_projects
        ''', conn)
        
        self.rejected_df = pd.read_sql_query('''
            SELECT *, 'rejected' as source FROM rejected_projects
        ''', conn)
        
        conn.close()
        
        # Convert dates
        for df in [self.raw_df, self.refined_df]:
            if 'date_created' in df.columns:
                df['date_created'] = pd.to_datetime(df['date_created'])
            if 'date_refined' in df.columns:
                df['date_refined'] = pd.to_datetime(df['date_refined'])
    
    def productivity_timeline(self):
        """Create timeline showing productivity over time"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
        
        # Monthly productivity
        monthly = self.refined_df.groupby(self.refined_df['date_created'].dt.to_period('ME')).size()
        monthly.plot(kind='line', ax=ax1, marker='o', linewidth=2)
        ax1.set_title('Monthly Music Productivity', fontsize=16, pad=20)
        ax1.set_ylabel('Projects Created')
        ax1.grid(True, alpha=0.3)
        
        # Cumulative projects over time
        cumulative = self.refined_df.set_index('date_created').resample('ME').size().cumsum()
        cumulative.plot(kind='area', ax=ax2, alpha=0.7)
        ax2.set_title('Cumulative Music Projects', fontsize=16, pad=20)
        ax2.set_ylabel('Total Projects')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig('productivity_timeline.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def genre_analysis(self):
        """Analyze genre distribution and evolution"""
        # Filter out null genres
        genre_data = self.refined_df[self.refined_df['genre'].notna()]
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Genre Distribution', 'Genre vs Rating', 
                          'Genre Evolution', 'Top Genres by Count'),
            specs=[[{"type": "pie"}, {"type": "box"}],
                   [{"type": "scatter"}, {"type": "bar"}]]
        )
        
        # Genre pie chart
        genre_counts = genre_data['genre'].value_counts()
        fig.add_trace(go.Pie(labels=genre_counts.index, values=genre_counts.values,
                            name="Genres"), row=1, col=1)
        
        # Genre vs Rating box plot
        for genre in genre_data['genre'].unique()[:8]:  # Top 8 genres
            genre_ratings = genre_data[genre_data['genre'] == genre]['rating']
            fig.add_trace(go.Box(y=genre_ratings, name=genre), row=1, col=2)
        
        # Genre evolution over time
        genre_data['year'] = genre_data['date_created'].dt.year
        for genre in genre_counts.head(5).index:  # Top 5 genres
            yearly_data = genre_data[genre_data['genre'] == genre].groupby('year').size()
            fig.add_trace(go.Scatter(x=yearly_data.index, y=yearly_data.values,
                                   mode='lines+markers', name=genre), row=2, col=1)
        
        # Top genres bar chart
        fig.add_trace(go.Bar(x=genre_counts.head(10).index, y=genre_counts.head(10).values,
                           name="Genre Counts"), row=2, col=2)
        
        fig.update_layout(height=800, showlegend=True, 
                          title_text="Genre Analysis Dashboard", title_x=0.5)
        fig.write_html('genre_analysis.html')
        fig.show()
    
    def completion_funnel(self):
        """Analyze project completion rates"""
        # Get status distribution
        status_counts = self.refined_df['status'].value_counts()
        
        # Create funnel chart
        fig = go.Figure(go.Funnel(
            y=status_counts.index,
            x=status_counts.values,
            textinfo="value+percent initial",
            marker_color=["deepskyblue", "lightsalmon", "tan", "teal", "silver"]
        ))
        
        fig.update_layout(
            title="Project Completion Funnel",
            font_size=14,
        )
        
        fig.write_html('completion_funnel.html')
        fig.show()
        
        # Completion rate by DAW
        completion_by_daw = self.refined_df.groupby('daw_type').agg({
            'status': ['count', lambda x: (x == 'complete').sum()]
        }).round(2)
        completion_by_daw.columns = ['Total', 'Completed']
        completion_by_daw['Completion_Rate'] = (completion_by_daw['Completed'] / completion_by_daw['Total'] * 100).round(1)
        
        print("Completion Rate by DAW:")
        print(completion_by_daw.sort_values('Completion_Rate', ascending=False))
    
    def rating_analysis(self):
        """Analyze project ratings and what makes a high-rated project"""
        rated_projects = self.refined_df[self.refined_df['rating'].notna()]
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Rating distribution
        rated_projects['rating'].hist(bins=10, ax=ax1, edgecolor='white', alpha=0.7)
        ax1.set_title('Rating Distribution')
        ax1.set_xlabel('Rating (1-10)')
        ax1.set_ylabel('Number of Projects')
        
        # Rating vs File Size
        ax2.scatter(rated_projects['file_size_mb'], rated_projects['rating'], alpha=0.6)
        ax2.set_xlabel('File Size (MB)')
        ax2.set_ylabel('Rating')
        ax2.set_title('Rating vs File Size')
        
        # Rating by DAW
        sns.boxplot(data=rated_projects, x='daw_type', y='rating', ax=ax3)
        ax3.set_title('Rating Distribution by DAW')
        ax3.tick_params(axis='x', rotation=45)
        
        # Rating over time
        monthly_rating = rated_projects.groupby(rated_projects['date_created'].dt.to_period('M'))['rating'].mean()
        monthly_rating.plot(ax=ax4, marker='o')
        ax4.set_title('Average Rating Over Time')
        ax4.set_ylabel('Average Rating')
        
        plt.tight_layout()
        plt.savefig('rating_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def collaboration_network(self):
        """Analyze collaborations"""
        collab_data = self.refined_df[self.refined_df['collaboration'].notna()]
        
        if len(collab_data) == 0:
            print("No collaboration data found")
            return
        
        # Parse collaborators
        all_collabs = []
        for collab_str in collab_data['collaboration']:
            if collab_str:
                collabs = [c.strip() for c in collab_str.split(',')]
                all_collabs.extend(collabs)
        
        collab_counts = Counter(all_collabs)
        
        # Top collaborators
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        top_collabs = dict(collab_counts.most_common(10))
        ax1.bar(top_collabs.keys(), top_collabs.values())
        ax1.set_title('Top Collaborators')
        ax1.tick_params(axis='x', rotation=45)
        
        # Collaboration frequency over time
        collab_data['year'] = collab_data['date_created'].dt.year
        yearly_collabs = collab_data.groupby('year').size()
        yearly_collabs.plot(kind='bar', ax=ax2)
        ax2.set_title('Collaborations by Year')
        ax2.set_ylabel('Number of Collaborative Projects')
        
        plt.tight_layout()
        plt.savefig('collaboration_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def tag_analysis(self):
        """Analyze tags and their relationships"""
        tagged_projects = self.refined_df[self.refined_df['tags'].notna()]
        
        if len(tagged_projects) == 0:
            print("No tag data found")
            return
        
        # Parse tags
        all_tags = []
        for tag_str in tagged_projects['tags']:
            if tag_str:
                try:
                    tags = json.loads(tag_str) if tag_str.startswith('[') else tag_str.split(',')
                    all_tags.extend([t.strip() for t in tags])
                except:
                    tags = tag_str.split(',')
                    all_tags.extend([t.strip() for t in tags])
        
        tag_counts = Counter(all_tags)
        
        # Tag frequency
        top_tags = dict(tag_counts.most_common(20))
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Tag bar chart
        ax1.barh(list(top_tags.keys()), list(top_tags.values()))
        ax1.set_title('Most Used Tags')
        ax1.set_xlabel('Frequency')
        
        # Tag word cloud effect (bar chart styled)
        sizes = list(top_tags.values())
        colors = plt.cm.viridis(np.linspace(0, 1, len(top_tags)))
        ax2.bar(range(len(top_tags)), sizes, color=colors)
        ax2.set_xticks(range(len(top_tags)))
        ax2.set_xticklabels(list(top_tags.keys()), rotation=45, ha='right')
        ax2.set_title('Tag Cloud (Frequency)')
        
        plt.tight_layout()
        plt.savefig('tag_analysis.png', dpi=300, bbox_inches='tight')
        plt.show()
    
    def project_lifecycle_analysis(self):
        """Analyze how projects move through the system"""
        total_raw = len(self.raw_df)
        total_refined = len(self.refined_df)
        total_rejected = len(self.rejected_df)
        unprocessed = total_raw - total_refined - total_rejected
        
        # Lifecycle funnel
        stages = ['Discovered', 'Refined', 'Unprocessed', 'Rejected']
        counts = [total_raw, total_refined, unprocessed, total_rejected]
        
        fig = go.Figure(go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=stages,
                color="blue"
            ),
            link=dict(
                source=[0, 0, 0],  # From Discovered
                target=[1, 2, 3],  # To Refined, Unprocessed, Rejected
                value=[total_refined, unprocessed, total_rejected]
            )
        ))
        
        fig.update_layout(title_text="Project Lifecycle Flow", font_size=10)
        fig.write_html('project_lifecycle.html')
        fig.show()
    
    def generate_report(self):
        """Generate comprehensive analytics report"""
        print("🎵 Music Tracker Analytics Report")
        print("=" * 50)
        
        self.load_data()
        
        # Basic stats
        print(f"📊 Overview:")
        print(f"   Total Projects Discovered: {len(self.raw_df)}")
        print(f"   Refined Projects: {len(self.refined_df)}")
        print(f"   Rejected Projects: {len(self.rejected_df)}")
        print(f"   Processing Rate: {len(self.refined_df)/len(self.raw_df)*100:.1f}%")
        
        # Time range
        if len(self.refined_df) > 0:
            earliest = self.refined_df['date_created'].min()
            latest = self.refined_df['date_created'].max()
            print(f"   Date Range: {earliest.strftime('%Y-%m-%d')} to {latest.strftime('%Y-%m-%d')}")
        
        print("\n🎯 Generating Visualizations...")
        
        # Generate all analyses
        try:
            self.productivity_timeline()
            print("   ✓ Productivity timeline created")
        except Exception as e:
            print(f"   ✗ Productivity timeline failed: {e}")
        
        try:
            self.genre_analysis()
            print("   ✓ Genre analysis created")
        except Exception as e:
            print(f"   ✗ Genre analysis failed: {e}")
        
        try:
            self.completion_funnel()
            print("   ✓ Completion funnel created")
        except Exception as e:
            print(f"   ✗ Completion funnel failed: {e}")
        
        try:
            self.rating_analysis()
            print("   ✓ Rating analysis created")
        except Exception as e:
            print(f"   ✗ Rating analysis failed: {e}")
        
        try:
            self.collaboration_network()
            print("   ✓ Collaboration analysis created")
        except Exception as e:
            print(f"   ✗ Collaboration analysis failed: {e}")
        
        try:
            self.tag_analysis()
            print("   ✓ Tag analysis created")
        except Exception as e:
            print(f"   ✗ Tag analysis failed: {e}")
        
        try:
            self.project_lifecycle_analysis()
            print("   ✓ Project lifecycle analysis created")
        except Exception as e:
            print(f"   ✗ Project lifecycle analysis failed: {e}")
        
        print("\n🎉 Analytics complete! Check generated files:")
        print("   - productivity_timeline.png")
        print("   - genre_analysis.html")
        print("   - completion_funnel.html")
        print("   - rating_analysis.png")
        print("   - collaboration_analysis.png")
        print("   - tag_analysis.png")
        print("   - project_lifecycle.html")


if __name__ == "__main__":
    import os
    
    # Default database path for macOS
    db_path = os.path.expanduser("~/Library/Application Support/MusicTracker/music_tracker.db")
    
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        print("Please provide correct path or run music-tracker to create database first")
        exit(1)
    
    analytics = MusicAnalytics(db_path)
    analytics.generate_report()
