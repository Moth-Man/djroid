#!/usr/bin/env python3
"""
Test script to simulate the crate command with a simple prompt.
Tests the core logic without requiring full database setup.
"""
import sys
import os
from pathlib import Path
from typing import Dict, List, Any

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Mock song data to simulate database results
MOCK_SONGS = [
    {
        'id': 1,
        'title': 'Techno Track 1',
        'artist': 'DJ Producer',
        'album': 'Peak Time',
        'genre': 'techno',
        'year': 2023,
        'bpm': 128.0,
        'key': 'Am',
        'filepath': '/music/techno_track_1.mp3',
        'popularimeter': 85,
        'file_size_mb': 8.5,
        'comment': 'Peak time banger'
    },
    {
        'id': 2,
        'title': 'Underground Anthem',
        'artist': 'Berlin Beats',
        'album': 'Warehouse Sessions',
        'genre': 'techno',
        'year': 2024,
        'bpm': 132.0,
        'key': 'Em',
        'filepath': '/music/underground_anthem.mp3',
        'popularimeter': 90,
        'file_size_mb': 9.2,
        'comment': 'Underground classic'
    },
    {
        'id': 3,
        'title': 'Dark Energy',
        'artist': 'Minimal Master',
        'album': 'After Hours',
        'genre': 'techno',
        'year': 2023,
        'bpm': 135.0,
        'key': 'Bm',
        'filepath': '/music/dark_energy.mp3',
        'popularimeter': 88,
        'file_size_mb': 7.8,
        'comment': 'Dark and driving'
    }
]

class MockSong:
    """Mock Song model to simulate database results"""
    def __init__(self, data):
        for key, value in data.items():
            setattr(self, key, value)

class MockSongDAO:
    """Mock DAO to simulate database queries"""
    def __init__(self):
        self.songs = [MockSong(song_data) for song_data in MOCK_SONGS]
    
    def search_songs(self, **kwargs) -> List[MockSong]:
        """Simulate database search with basic filtering"""
        results = self.songs[:]
        
        if 'genre' in kwargs and kwargs['genre']:
            results = [s for s in results if s.genre and kwargs['genre'].lower() in s.genre.lower()]
        
        if 'bpm_min' in kwargs and kwargs['bpm_min']:
            results = [s for s in results if s.bpm and s.bpm >= kwargs['bpm_min']]
        
        if 'bpm_max' in kwargs and kwargs['bpm_max']:
            results = [s for s in results if s.bpm and s.bpm <= kwargs['bpm_max']]
        
        if 'energy_min' in kwargs and kwargs['energy_min']:
            results = [s for s in results if s.popularimeter and s.popularimeter >= kwargs['energy_min']]
        
        if 'energy_max' in kwargs and kwargs['energy_max']:
            results = [s for s in results if s.popularimeter and s.popularimeter <= kwargs['energy_max']]
        
        print(f"🔍 Mock database query with filters: {kwargs}")
        print(f"📊 Found {len(results)} matching songs")
        
        return results

def test_agents():
    """Test the LangChain agents with a simple prompt"""
    try:
        print("🤖 Testing LangChain agents...")
        
        # Import our agent tools
        from djroid.llm.agents import BPMKeyAnalysisTool, TagAnalysisTool, DurationAnalysisTool
        
        # Test prompt
        test_prompt = "give me 3 hard techno songs for peak time"
        print(f"📝 Test prompt: '{test_prompt}'")
        
        # Test BPM/Key analysis
        print("\n🎵 BPM/Key Analysis:")
        bpm_tool = BPMKeyAnalysisTool()
        bpm_result = bpm_tool._run(test_prompt)
        print(f"   BPM Range: {bpm_result.get('bpm_range', 'N/A')}")
        print(f"   Energy: {bpm_result.get('energy_requirements', 'N/A')}")
        print(f"   Template: {bpm_result.get('set_template', 'N/A')}")
        
        # Test Tag analysis
        print("\n🏷️  Tag Analysis:")
        tag_tool = TagAnalysisTool()
        tag_result = tag_tool._run(test_prompt)
        print(f"   Genres: {tag_result.get('identified_genres', 'N/A')}")
        print(f"   Mood: {tag_result.get('mood_requirements', 'N/A')}")
        
        # Test Duration analysis
        print("\n⏱️  Duration Analysis:")
        duration_tool = DurationAnalysisTool()
        duration_result = duration_tool._run(test_prompt)
        print(f"   Target Songs: {duration_result.get('target_song_count', 'N/A')}")
        print(f"   Estimated Duration: {duration_result.get('estimated_playtime', 'N/A')} minutes")
        
        return bpm_result, tag_result, duration_result
        
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None

def test_database_query(bpm_result, tag_result):
    """Test database querying with analysis results"""
    try:
        print("\n🗄️  Testing database query...")
        
        # Create mock DAO
        mock_dao = MockSongDAO()
        
        # Build query parameters from analysis
        query_params = {}
        
        if tag_result and tag_result.get('identified_genres'):
            query_params['genre'] = tag_result['identified_genres'][0]
        
        if bpm_result and bpm_result.get('bpm_range'):
            query_params['bpm_min'] = bpm_result['bpm_range'][0]
            query_params['bpm_max'] = bpm_result['bpm_range'][1]
        
        if bpm_result and bpm_result.get('energy_requirements'):
            energy = bpm_result['energy_requirements']
            query_params['energy_min'] = energy.get('min')
            query_params['energy_max'] = energy.get('max')
        
        # Execute query
        songs = mock_dao.search_songs(**query_params)
        
        print(f"\n📚 Query Results ({len(songs)} songs):")
        for i, song in enumerate(songs[:3], 1):  # Limit to 3 songs
            print(f"   {i}. {song.title} by {song.artist}")
            print(f"      BPM: {song.bpm}, Key: {song.key}, Energy: {song.popularimeter}")
            print(f"      Path: {song.filepath}")
        
        return songs[:3]  # Return first 3 songs
        
    except Exception as e:
        print(f"❌ Database query test failed: {e}")
        import traceback
        traceback.print_exc()
        return []

def test_playlist_generation(songs):
    """Test playlist file generation"""
    try:
        print("\n📁 Testing playlist generation...")
        
        from djroid.llm.playlist_generators import M3UGenerator, PlaylistOrganizer
        
        # Convert mock songs to dictionaries
        song_dicts = []
        for song in songs:
            song_dict = {
                'title': song.title,
                'artist': song.artist,
                'album': song.album,
                'genre': song.genre,
                'year': song.year,
                'bpm': song.bpm,
                'key': song.key,
                'filepath': song.filepath,
                'duration': 210,  # 3.5 minutes
                'popularimeter': song.popularimeter,
                'file_size_mb': song.file_size_mb,
                'comment': song.comment
            }
            song_dicts.append(song_dict)
        
        # Test organization
        organizer = PlaylistOrganizer()
        organized_songs = organizer.organize_by_template(song_dicts, "build_up_peak_cooldown")
        print(f"🎚️  Organized {len(organized_songs)} songs by template")
        
        # Generate M3U playlist
        m3u_generator = M3UGenerator()
        output_path = Path("./test_output")
        output_path.mkdir(exist_ok=True)
        
        playlist_file = m3u_generator.generate(organized_songs, output_path, "test_techno_set")
        print(f"✅ M3U playlist generated: {playlist_file}")
        
        # Read and display the generated playlist
        if os.path.exists(playlist_file):
            print(f"\n📄 Generated playlist content:")
            with open(playlist_file, 'r') as f:
                content = f.read()
                print(content)
        
        return playlist_file
        
    except Exception as e:
        print(f"❌ Playlist generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Run the complete test"""
    print("🧪 DJroid Crate Command Test")
    print("=" * 50)
    
    # Test 1: Agent analysis
    bpm_result, tag_result, duration_result = test_agents()
    
    if not bpm_result or not tag_result:
        print("❌ Agent tests failed, skipping remaining tests")
        return
    
    # Test 2: Database query simulation
    songs = test_database_query(bpm_result, tag_result)
    
    if not songs:
        print("❌ No songs found, skipping playlist generation")
        return
    
    # Test 3: Playlist generation
    playlist_file = test_playlist_generation(songs)
    
    if playlist_file:
        print(f"\n🎉 Test completed successfully!")
        print(f"📊 Generated playlist with {len(songs)} songs")
        print(f"📁 Output file: {playlist_file}")
    else:
        print("❌ Playlist generation failed")

if __name__ == "__main__":
    main()