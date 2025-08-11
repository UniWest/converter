#!/usr/bin/env python3
"""
Creates sample media files for testing purposes.
These are minimal valid media files for form validation and integration tests.
"""
import os
from pathlib import Path

def create_sample_mp4():
    """Create a minimal valid MP4 file for testing"""
    # This is a minimal MP4 header that creates a valid but tiny video file
    mp4_data = bytes([
        # ftyp box
        0x00, 0x00, 0x00, 0x20, 0x66, 0x74, 0x79, 0x70,  # size + ftyp
        0x69, 0x73, 0x6f, 0x6d, 0x00, 0x00, 0x02, 0x00,  # isom + version
        0x69, 0x73, 0x6f, 0x6d, 0x69, 0x73, 0x6f, 0x32,  # compatible brands
        0x61, 0x76, 0x63, 0x31, 0x6d, 0x70, 0x34, 0x31,  # more brands
        # mdat box (minimal)
        0x00, 0x00, 0x00, 0x08, 0x6d, 0x64, 0x61, 0x74,  # size + mdat
    ])
    return mp4_data

def create_sample_files():
    """Create all sample files for testing"""
    media_dir = Path(__file__).parent / 'media'
    media_dir.mkdir(exist_ok=True)
    
    # Create sample MP4 files of different sizes
    files_created = []
    
    # Small valid MP4 (40 bytes)
    small_mp4_path = media_dir / 'small_sample.mp4'
    with open(small_mp4_path, 'wb') as f:
        f.write(create_sample_mp4())
    files_created.append(small_mp4_path)
    print(f"Created: {small_mp4_path} ({small_mp4_path.stat().st_size} bytes)")
    
    # Medium MP4 (1KB)
    medium_mp4_path = media_dir / 'medium_sample.mp4'
    with open(medium_mp4_path, 'wb') as f:
        base_data = create_sample_mp4()
        # Pad with zeros to make it 1KB
        padding = b'\x00' * (1024 - len(base_data))
        f.write(base_data + padding)
    files_created.append(medium_mp4_path)
    print(f"Created: {medium_mp4_path} ({medium_mp4_path.stat().st_size} bytes)")
    
    # Create invalid files for testing
    # Too big file (simulated by creating a file > 500MB marker)
    big_marker_path = media_dir / 'big_file_marker.txt'
    with open(big_marker_path, 'w') as f:
        f.write("This file represents a >500MB video for testing size validation")
    files_created.append(big_marker_path)
    
    # Wrong format file
    wrong_format_path = media_dir / 'wrong_format.txt'
    with open(wrong_format_path, 'w') as f:
        f.write("This is not a video file")
    files_created.append(wrong_format_path)
    
    # Invalid time test data
    invalid_times_path = media_dir / 'invalid_times.json'
    import json
    invalid_time_cases = [
        {"start_time": -5, "end_time": 10, "error": "negative start time"},
        {"start_time": 20, "end_time": 10, "error": "end time before start time"},
        {"start_time": 0, "end_time": 700, "error": "duration > 10 minutes"},
        {"start_time": 5, "end_time": 5, "error": "zero duration"},
    ]
    with open(invalid_times_path, 'w') as f:
        json.dump(invalid_time_cases, f, indent=2)
    files_created.append(invalid_times_path)
    
    return files_created

if __name__ == '__main__':
    files = create_sample_files()
    print(f"\nCreated {len(files)} test files:")
    for file_path in files:
        print(f"  - {file_path}")
