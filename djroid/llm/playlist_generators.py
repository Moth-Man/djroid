"""
Playlist generation utilities for M3U and Rekordbox XML formats.
"""
from typing import List, Dict, Any
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom
from urllib.parse import quote
from djroid.logging import get_logger

logger = get_logger(__name__)

class PlaylistGenerator:
    """Base class for playlist generation"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def generate_playlist_name(self, prompt: str) -> str:
        """Generate a playlist name from the user prompt"""
        # Clean the prompt and create a reasonable filename
        import re
        clean_prompt = re.sub(r'[^\w\s-]', '', prompt).strip()
        clean_prompt = re.sub(r'\s+', '_', clean_prompt)
        return clean_prompt[:50] + "_playlist"  # Limit length

class M3UGenerator(PlaylistGenerator):
    """M3U playlist generator"""
    
    def generate(self, songs: List[Dict[str, Any]], output_path: Path, playlist_name: str) -> str:
        """Generate M3U playlist file"""
        logger.info(f"Generating M3U playlist: {playlist_name}")
        
        output_file = output_path / f"{playlist_name}.m3u"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            
            for song in songs:
                # Calculate duration in seconds (estimate 3.5 minutes if not available)
                duration = int(song.get('duration', 210))  # 3.5 minutes default
                
                title = song.get('title', 'Unknown Title')
                artist = song.get('artist', 'Unknown Artist')
                filepath = song.get('filepath', '')
                
                # Write extended info
                f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                f.write(f"{filepath}\n")
        
        logger.info(f"M3U playlist generated: {output_file}")
        return str(output_file)

class RekordboxXMLGenerator(PlaylistGenerator):
    """Rekordbox XML playlist generator"""
    
    def generate(self, songs: List[Dict[str, Any]], output_path: Path, playlist_name: str) -> str:
        """Generate Rekordbox XML playlist file"""
        logger.info(f"Generating Rekordbox XML playlist: {playlist_name}")
        
        # Create XML structure
        root = ET.Element("DJ_PLAYLISTS", Version="1.0.0")
        
        # Product info
        product = ET.SubElement(root, "PRODUCT", Name="DJroid", Version="1.0", Company="DJroid")
        
        # Collection
        collection = ET.SubElement(root, "COLLECTION", Entries=str(len(songs)))
        
        # Add tracks to collection
        for i, song in enumerate(songs, 1):
            # Helper function to safely convert values to strings, handling None
            def safe_str(value, default=""):
                if value is None:
                    return default
                return str(value)
            
            # Helper function to safely get file size
            def safe_file_size(size_mb):
                if size_mb is None or size_mb == 0:
                    return "0"
                return str(int(size_mb * 1024 * 1024))
            
            track_attrs = {
                "TrackID": str(i),
                "Name": safe_str(song.get('title'), 'Unknown Title'),
                "Artist": safe_str(song.get('artist'), 'Unknown Artist'),
                "Album": safe_str(song.get('album'), ''),
                "Genre": safe_str(song.get('genre'), ''),
                "Kind": "MP3 File",  # Default to MP3
                "Size": safe_file_size(song.get('file_size_mb')),
                "TotalTime": safe_str(int(song.get('duration', 210))),
                "Year": safe_str(song.get('year'), ''),
                "AverageBpm": f"{song.get('bpm', 0):.1f}" if song.get('bpm') else "0.0",
                "DateAdded": "2024-01-01",  # Default date
                "BitRate": "320",  # Default bitrate
                "SampleRate": "44100",  # Default sample rate
                "Comments": safe_str(song.get('comment'), ''),
                "PlayCount": "0",
                "Rating": "0",
                "Location": f"file://localhost{quote(safe_str(song.get('filepath'), ''))}"
            }
            
            # Add Camelot key if available
            if song.get('key'):
                track_attrs["Tonality"] = self._convert_to_camelot(song['key'])
            
            # Add energy level if available
            if song.get('popularimeter'):
                track_attrs["Ranking"] = safe_str(song['popularimeter'])
            
            track = ET.SubElement(collection, "TRACK", **track_attrs)
        
        # Playlists section
        playlists = ET.SubElement(root, "PLAYLISTS")
        root_node = ET.SubElement(playlists, "NODE", Type="0", Name="ROOT", Count="1")
        playlist_node = ET.SubElement(
            root_node, 
            "NODE", 
            Type="1", 
            Name=playlist_name, 
            Entries=str(len(songs)), 
            KeyType="0"
        )
        
        # Add track references to playlist
        for i in range(1, len(songs) + 1):
            ET.SubElement(playlist_node, "TRACK", Key=str(i))
        
        # Pretty print XML
        rough_string = ET.tostring(root, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="    ", encoding='utf-8')
        
        # Write to file
        output_file = output_path / f"{playlist_name}.xml"
        with open(output_file, 'wb') as f:
            f.write(pretty_xml)
        
        logger.info(f"Rekordbox XML playlist generated: {output_file}")
        return str(output_file)
    
    def _convert_to_camelot(self, key: str) -> str:
        """Convert musical key to Camelot notation"""
        camelot_map = {
            "C": "8B", "Cm": "8A", "Am": "8A", "C major": "8B", "C minor": "8A", "A minor": "8A",
            "G": "9B", "Gm": "9A", "Em": "9A", "G major": "9B", "G minor": "9A", "E minor": "9A",
            "D": "10B", "Dm": "10A", "Bm": "10A", "D major": "10B", "D minor": "10A", "B minor": "10A",
            "A": "11B", "Am": "11A", "F#m": "11A", "A major": "11B", "A minor": "11A", "F# minor": "11A",
            "E": "12B", "Em": "12A", "C#m": "12A", "E major": "12B", "E minor": "12A", "C# minor": "12A",
            "B": "1B", "Bm": "1A", "G#m": "1A", "B major": "1B", "B minor": "1A", "G# minor": "1A",
            "F#": "2B", "F#m": "2A", "D#m": "2A", "F# major": "2B", "F# minor": "2A", "D# minor": "2A",
            "Db": "3B", "Dbm": "3A", "Bbm": "3A", "Db major": "3B", "Db minor": "3A", "Bb minor": "3A",
            "Ab": "4B", "Abm": "4A", "Fm": "4A", "Ab major": "4B", "Ab minor": "4A", "F minor": "4A",
            "Eb": "5B", "Ebm": "5A", "Cm": "5A", "Eb major": "5B", "Eb minor": "5A", "C minor": "5A",
            "Bb": "6B", "Bbm": "6A", "Gm": "6A", "Bb major": "6B", "Bb minor": "6A", "G minor": "6A",
            "F": "7B", "Fm": "7A", "Dm": "7A", "F major": "7B", "F minor": "7A", "D minor": "7A",
        }
        
        return camelot_map.get(key, key)  # Return original if not found

class PlaylistOrganizer:
    """Organizes songs according to DJ set templates"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def _get_bpm(self, song):
        """Get BPM from song object or dict"""
        if hasattr(song, 'bpm'):
            return song.bpm or 120
        elif isinstance(song, dict):
            return song.get('bpm', 120)
        return 120
    
    def organize_by_template(self, songs: List[Dict[str, Any]], template: str) -> List[Dict[str, Any]]:
        """Organize songs according to set template"""
        logger.info(f"Organizing {len(songs)} songs by template: {template}")
        
        if not songs:
            return songs
        
        # Sort songs by BPM first for basic flow
        # Handle both dict and Song object types
        songs_with_bpm = [s for s in songs if (hasattr(s, 'bpm') and s.bpm) or (isinstance(s, dict) and s.get('bpm'))]
        songs_without_bpm = [s for s in songs if not ((hasattr(s, 'bpm') and s.bpm) or (isinstance(s, dict) and s.get('bpm')))]
        
        songs_with_bpm.sort(key=self._get_bpm)
        
        if template == "build_up_peak_cooldown":
            return self._build_up_peak_cooldown(songs_with_bpm) + songs_without_bpm
        elif template == "constantly_building":
            return self._constantly_building(songs_with_bpm) + songs_without_bpm
        elif template == "peak_sustain_peak":
            return self._peak_sustain_peak(songs_with_bpm) + songs_without_bpm
        elif template == "gradual_build":
            return self._gradual_build(songs_with_bpm) + songs_without_bpm
        else:
            # Default: just sort by BPM
            return songs_with_bpm + songs_without_bpm
    
    def _build_up_peak_cooldown(self, songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Classic DJ structure: 30% build, 20% peak, 20% cooldown, 20% second peak, 10% closer"""
        if len(songs) < 5:
            return songs
        
        # Divide songs into sections
        total = len(songs)
        build_end = int(total * 0.3)
        peak1_end = build_end + int(total * 0.2)
        cooldown_end = peak1_end + int(total * 0.2)
        peak2_end = cooldown_end + int(total * 0.2)
        
        # Sort different sections
        low_energy = sorted(songs[:build_end], key=self._get_bpm)
        high_energy = sorted(songs[build_end:peak1_end], key=self._get_bpm, reverse=True)
        mid_energy = sorted(songs[peak1_end:cooldown_end], key=self._get_bpm)
        high_energy2 = sorted(songs[cooldown_end:peak2_end], key=self._get_bpm, reverse=True)
        closers = sorted(songs[peak2_end:], key=self._get_bpm)
        
        return low_energy + high_energy + mid_energy + high_energy2 + closers
    
    def _constantly_building(self, songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """For hard dance/techno: steady energy increase"""
        return sorted(songs, key=self._get_bpm)
    
    def _peak_sustain_peak(self, songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """For mainstream sets: quick to peak, sustain, second peak"""
        if len(songs) < 3:
            return songs
        
        # Quick build, then high energy throughout
        intro = songs[:2]
        main_set = sorted(songs[2:], key=self._get_bpm, reverse=True)
        
        return intro + main_set
    
    def _gradual_build(self, songs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """For ambient/progressive: very gradual energy increase"""
        return sorted(songs, key=self._get_bpm)