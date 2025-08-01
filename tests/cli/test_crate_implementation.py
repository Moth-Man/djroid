#!/usr/bin/env python3
"""
Simple test script to verify the crate implementation works
without requiring full environment setup.
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

# Test the core classes can be imported and instantiated
try:
    print("Testing imports...")
    
    # Test agent imports
    from djroid.llm.agents import BPMKeyAnalysisTool, TagAnalysisTool, DurationAnalysisTool, SupervisorAgent
    print("✅ Agent imports successful")
    
    # Test playlist generator imports
    from djroid.llm.playlist_generators import M3UGenerator, RekordboxXMLGenerator, PlaylistOrganizer
    print("✅ Playlist generator imports successful")
    
    # Test instantiation
    bpm_tool = BPMKeyAnalysisTool()
    tag_tool = TagAnalysisTool()
    duration_tool = DurationAnalysisTool()
    print("✅ Tool instantiation successful")
    
    # Test basic tool functionality
    print("\nTesting tool functionality...")
    
    test_prompt = "give me 10 hard techno songs for peak time"
    
    bpm_result = bpm_tool._run(test_prompt)
    print(f"✅ BPM analysis: {bpm_result}")
    
    tag_result = tag_tool._run(test_prompt)
    print(f"✅ Tag analysis: {tag_result}")
    
    duration_result = duration_tool._run(test_prompt)
    print(f"✅ Duration analysis: {duration_result}")
    
    # Test playlist generators
    print("\nTesting playlist generators...")
    
    m3u_gen = M3UGenerator()
    xml_gen = RekordboxXMLGenerator()
    organizer = PlaylistOrganizer()
    print("✅ Generator instantiation successful")
    
    # Test sample data organization
    sample_songs = [
        {"title": "Track 1", "artist": "Artist 1", "bpm": 128, "filepath": "/path/to/track1.mp3"},
        {"title": "Track 2", "artist": "Artist 2", "bpm": 132, "filepath": "/path/to/track2.mp3"},
        {"title": "Track 3", "artist": "Artist 3", "bpm": 135, "filepath": "/path/to/track3.mp3"},
    ]
    
    organized = organizer.organize_by_template(sample_songs, "build_up_peak_cooldown")
    print(f"✅ Song organization successful: {len(organized)} songs organized")
    
    print("\n🎉 All core components are working correctly!")
    print("\nTo complete the setup:")
    print("1. Set up a virtual environment: python3 -m venv venv")
    print("2. Activate it: source venv/bin/activate")
    print("3. Install dependencies: pip install -e .")
    print("4. Set OPENAI_API_KEY environment variable")
    print("5. Initialize the database")
    print("6. Test with: djroid crate 'give me 10 techno songs'")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()