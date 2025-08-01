"""
Fixed version of crate service for multi-genre queries.
"""
from typing import Dict, List, Any, Optional
from pathlib import Path
import os
from datetime import datetime

from djroid.logging import get_logger
from djroid.db import get_db
from djroid.db.dao.song_dao import SongDAO
from djroid.llm.agents import SupervisorAgent, QueryPlan
from djroid.llm.playlist_generators import M3UGenerator, RekordboxXMLGenerator, PlaylistOrganizer

logger = get_logger(__name__)

class Crate:
    """Main service for crate/playlist generation with multi-genre support"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.supervisor = None
        self.song_dao = None
        
    def _initialize_components(self):
        """Initialize LLM and database components"""
        try:
            # Initialize LangChain supervisor agent
            self.supervisor = SupervisorAgent()
            self.logger.info("Supervisor agent initialized")
            
            # Initialize database access - get_db() is a generator, so we need to get the next value
            db_generator = get_db()
            db = next(db_generator)
            self.song_dao = SongDAO(db)
            self.db_session = db  # Keep reference to close later
            self.db_generator = db_generator  # Keep reference to generator
            self.logger.info("Database connection initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            raise
    
    def _cleanup(self):
        """Clean up database connections"""
        try:
            if hasattr(self, 'db_session') and self.db_session:
                self.db_session.close()
                self.logger.debug("Database session closed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def generate_crate(self, prompt: str, output_path: Optional[str] = None, 
                      usb_format: bool = False) -> Dict[str, Any]:
        """
        Generate a curated playlist based on user prompt.
        
        Args:
            prompt: Natural language description of desired playlist
            output_path: Directory to save playlist (default: current directory)
            usb_format: If True, generate Rekordbox XML; otherwise M3U
            
        Returns:
            Dict with success status, playlist path, song count, and duration
        """
        self.logger.info(f"Starting crate generation for prompt: {prompt}")
        
        try:
            # Initialize components
            self._initialize_components()
            
            try:
                # Step 1: Analyze prompt using LangChain supervisor
                self.logger.info("Step 1: Analyzing user prompt")
                query_plan = self.supervisor.analyze_prompt(prompt)
                self.logger.info(f"Generated query plan: {query_plan}")
                
                # Step 2: Query database for matching songs
                self.logger.info("Step 2: Querying database for songs")
                songs = self._query_songs(query_plan)
                
                if not songs:
                    return {
                        "success": False,
                        "error": "No songs found matching your criteria. Try broadening your request or adding more music to your library.",
                        "playlist_path": None,
                        "song_count": 0,
                        "duration": "0:00"
                    }
                
                self.logger.info(f"Found {len(songs)} matching songs")
                
                # Step 3: Organize songs according to set template
                self.logger.info("Step 3: Organizing songs by set template")
                organizer = PlaylistOrganizer()
                organized_songs = organizer.organize_by_template(songs, query_plan.set_template)
                
                # Step 4: Limit to target song count if specified
                if query_plan.target_song_count and len(organized_songs) > query_plan.target_song_count:
                    organized_songs = organized_songs[:query_plan.target_song_count]
                    self.logger.info(f"Limited to {query_plan.target_song_count} songs")
                
                # Step 5: Generate playlist file
                self.logger.info("Step 5: Generating playlist file")
                output_dir = Path(output_path) if output_path else Path.cwd()
                output_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate playlist name from prompt
                playlist_name = self._generate_playlist_name(prompt)
                
                # Choose generator based on format
                if usb_format:
                    generator = RekordboxXMLGenerator()
                else:
                    generator = M3UGenerator()
                
                # Convert songs to dictionaries for generator
                song_dicts = [self._song_to_dict(song) for song in organized_songs]
                
                playlist_path = generator.generate(song_dicts, output_dir, playlist_name)
                
                # Calculate total duration
                total_duration = self._calculate_duration(organized_songs)
                
                self.logger.info(f"Crate generation completed successfully: {playlist_path}")
                
                return {
                    "success": True,
                    "playlist_path": playlist_path,
                    "song_count": len(organized_songs),
                    "duration": total_duration,
                    "format": "Rekordbox XML" if usb_format else "M3U",
                    "template_used": query_plan.set_template
                }
                
            finally:
                # Clean up database connection
                self._cleanup()
            
        except Exception as e:
            self.logger.error(f"Crate generation failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "playlist_path": None,
                "song_count": 0,
                "duration": "0:00"
            }
    
    def _query_songs(self, query_plan: QueryPlan) -> List[Any]:
        """Query database using the generated query plan with multi-genre support"""
        try:
            self.logger.info(f"Querying for genres: {query_plan.genre_filters}")
            
            # Query for multiple genres and combine results
            all_songs = []
            
            if query_plan.genre_filters:
                # Query each genre separately and combine results
                for genre in query_plan.genre_filters:
                    query_params = {'genre': genre}
                    
                    # Add BPM range if specified
                    if query_plan.bpm_range:
                        query_params['bpm_min'] = query_plan.bpm_range[0]
                        query_params['bpm_max'] = query_plan.bpm_range[1]
                    
                    # Add energy requirements if specified
                    if query_plan.energy_requirements:
                        query_params['energy_min'] = query_plan.energy_requirements.get('min')
                        query_params['energy_max'] = query_plan.energy_requirements.get('max')
                    
                    self.logger.info(f"Querying for genre '{genre}' with params: {query_params}")
                    genre_songs = self.song_dao.search_songs(**query_params)
                    
                    # If strict search finds nothing, try just genre
                    if not genre_songs:
                        self.logger.info(f"No strict results for '{genre}', trying genre-only search")
                        genre_songs = self.song_dao.search_songs(genre=genre)
                    
                    self.logger.info(f"Found {len(genre_songs)} songs for genre '{genre}'")
                    all_songs.extend(genre_songs)
                
                # Remove duplicates while preserving order
                seen_ids = set()
                unique_songs = []
                for song in all_songs:
                    if song.id not in seen_ids:
                        seen_ids.add(song.id)
                        unique_songs.append(song)
                
                all_songs = unique_songs
            else:
                # No genre filters, use other criteria
                query_params = {}
                
                if query_plan.bpm_range:
                    query_params['bpm_min'] = query_plan.bpm_range[0]
                    query_params['bpm_max'] = query_plan.bpm_range[1]
                
                if query_plan.energy_requirements:
                    query_params['energy_min'] = query_plan.energy_requirements.get('min')
                    query_params['energy_max'] = query_plan.energy_requirements.get('max')
                
                if query_params:
                    all_songs = self.song_dao.search_songs(**query_params)
                else:
                    # Get all songs if no specific criteria
                    all_songs = self.song_dao.get_all_songs(limit=100)
            
            self.logger.info(f"Total unique songs found: {len(all_songs)}")
            return all_songs
            
        except Exception as e:
            self.logger.error(f"Database query failed: {e}")
            # Return empty list to allow graceful degradation
            return []
    
    def _generate_playlist_name(self, prompt: str) -> str:
        """Generate a suitable playlist name from the prompt"""
        import re
        
        # Clean and shorten the prompt
        clean_prompt = re.sub(r'[^\w\s-]', '', prompt).strip()
        clean_prompt = re.sub(r'\s+', '_', clean_prompt)
        
        # Limit length and add timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        base_name = clean_prompt[:30] if clean_prompt else "djroid_crate"
        
        return f"{base_name}_{timestamp}"
    
    def _song_to_dict(self, song) -> Dict[str, Any]:
        """Convert Song model to dictionary for playlist generation"""
        return {
            'title': song.title,
            'artist': song.artist,
            'album': song.album,
            'genre': song.genre,
            'year': song.year,
            'bpm': song.bpm,
            'key': song.key,
            'filepath': song.filepath,
            'duration': 210,  # Default 3.5 minutes, could be calculated from file
            'file_size_mb': song.file_size_mb,
            'comment': song.comment,
            'popularimeter': song.popularimeter
        }
    
    def _calculate_duration(self, songs: List[Any]) -> str:
        """Calculate total playlist duration"""
        # Estimate duration (3.5 minutes per song on average)
        total_minutes = len(songs) * 3.5
        hours = int(total_minutes // 60)
        minutes = int(total_minutes % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"