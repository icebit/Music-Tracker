#!/usr/bin/env python3
"""
Setup script for Music Project Tracker
"""

from setuptools import setup, find_packages
import os

# Read version from the main module
version = "1.1.0"
try:
    # Try to read version from the package
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'music_tracker'))
    from music_tracker import __version__
    version = __version__
except ImportError:
    pass

setup(
    name="music-tracker",
    version=version,
    description="Advanced CLI tool for tracking DAW music projects",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "music-tracker=music_tracker.music_tracker:main",
            "mt=music_tracker.music_tracker:main",
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
)
