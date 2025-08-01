"""
LangChain-based agent system for intelligent playlist generation.
Implements supervisor and sub-agent architecture for DJ crate generation.
"""
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.tools import BaseTool
from langchain.schema import BaseMessage, HumanMessage, SystemMessage
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
import json
import os
from djroid.logging import get_logger

logger = get_logger(__name__)

# Pydantic Models for Structured Outputs
class BPMKeyAnalysisOutput(BaseModel):
    bpm_range: Tuple[float, float] = Field(description="Recommended BPM range (min, max)")
    key_progression: List[str] = Field(description="Camelot key progression for the set")
    set_template: str = Field(description="Set structure template")
    energy_requirements: Dict[str, int] = Field(description="Energy level requirements")

class TagAnalysisOutput(BaseModel):
    identified_genres: List[str] = Field(description="Genres identified from prompt")
    energy_requirements: Dict[str, Any] = Field(description="Energy level and progression")
    mood_requirements: List[str] = Field(description="Mood descriptors")
    suggested_queries: List[Dict[str, Any]] = Field(description="Database query suggestions")

class DurationAnalysisOutput(BaseModel):
    target_duration_minutes: Optional[int] = Field(description="Target duration in minutes")
    target_song_count: Optional[int] = Field(description="Target number of songs")
    transition_time_per_song: float = Field(description="Average transition time per song")
    estimated_playtime: float = Field(description="Estimated total playtime")

class QueryPlan(BaseModel):
    genre_filters: List[str] = Field(default_factory=list)
    bpm_range: Optional[Tuple[float, float]] = None
    key_filters: List[str] = Field(default_factory=list)
    energy_requirements: Optional[Dict[str, Any]] = None
    target_song_count: Optional[int] = None
    set_template: str = Field(description="Set structure template")
    tag_filters: Optional[Dict[str, Any]] = None

# Camelot Wheel Mapping
CAMELOT_WHEEL = {
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

# Set Templates
SET_TEMPLATES = {
    "build_up_peak_cooldown": {
        "description": "Classic DJ structure (30% build, 20% peak, 20% cooldown, 20% second peak, 10% closer)",
        "energy_progression": [0.3, 0.7, 1.0, 0.6, 0.9, 0.4],
        "bpm_progression": "gradual_increase_then_decrease"
    },
    "constantly_building": {
        "description": "For hard dance/techno (10% intro, 40% build, 40% peak, 10% closer)",
        "energy_progression": [0.2, 0.5, 0.8, 1.0, 0.3],
        "bpm_progression": "steady_increase"
    },
    "peak_sustain_peak": {
        "description": "For mainstream sets",
        "energy_progression": [0.4, 0.9, 0.8, 0.9, 0.5],
        "bpm_progression": "plateau_with_variations"
    },
    "gradual_build": {
        "description": "For ambient/progressive genres",
        "energy_progression": [0.1, 0.3, 0.5, 0.7, 0.4],
        "bpm_progression": "very_gradual_increase"
    }
}

# Tag Schema Structure
DEFAULT_TAG_SCHEMA = {
    "function": ["intro", "build", "drop", "breakdown", "outro"],
    "utility": ["warmup", "peak time", "closing", "backup"],
    "setting": ["club", "festival", "warehouse", "outdoor"],
    "situation": ["crowd control", "energy boost", "chill out"],
    "demographic": ["underground", "mainstream", "experimental"]
}

class BPMKeyAnalysisTool(BaseTool):
    name: str = "bpm_key_energy_analysis"
    description: str = "Analyze BPM progression, key compatibility, and energy flow for DJ sets"
    
    def _run(self, user_prompt: str, target_duration: Optional[int] = None, 
              genre_requirements: List[str] = None) -> Dict[str, Any]:
        """Analyze musical flow requirements from user prompt"""
        logger.info(f"Analyzing BPM/Key/Energy for prompt: {user_prompt}")
        
        # Basic analysis based on genre keywords
        prompt_lower = user_prompt.lower()
        
        # Determine BPM range based on genres mentioned
        if any(genre in prompt_lower for genre in ["techno", "hard dance", "hardcore"]):
            bpm_range = (130, 150)
            set_template = "constantly_building"
            energy_min, energy_max = 80, 100
        elif any(genre in prompt_lower for genre in ["house", "progressive"]):
            bpm_range = (120, 130)
            set_template = "gradual_build"
            energy_min, energy_max = 60, 90
        elif any(genre in prompt_lower for genre in ["trance", "uplifting"]):
            bpm_range = (128, 138)
            set_template = "build_up_peak_cooldown"
            energy_min, energy_max = 70, 100
        elif any(genre in prompt_lower for genre in ["trap", "hip hop", "rap"]):
            bpm_range = (70, 90)
            set_template = "peak_sustain_peak"
            energy_min, energy_max = 70, 95
        else:
            # Default range for mixed/unspecified genres
            bpm_range = (120, 135)
            set_template = "build_up_peak_cooldown"
            energy_min, energy_max = 60, 90
        
        # Generate key progression (simplified)
        key_progression = ["8B", "9B", "10B", "9B", "8B"]  # Classic progression
        
        return {
            "bpm_range": bpm_range,
            "key_progression": key_progression,
            "set_template": set_template,
            "energy_requirements": {"min": energy_min, "max": energy_max}
        }

class TagAnalysisTool(BaseTool):
    name: str = "tag_schema_analysis"
    description: str = "Analyze user prompt against tag schema to create database queries"
    
    def _run(self, user_prompt: str, tag_schema: Dict[str, List[str]] = None) -> Dict[str, Any]:
        """Map user prompt to database query parameters"""
        logger.info(f"Analyzing tags for prompt: {user_prompt}")
        
        if not tag_schema:
            tag_schema = DEFAULT_TAG_SCHEMA
        
        prompt_lower = user_prompt.lower()
        identified_genres = []
        mood_requirements = []
        suggested_queries = []
        
        # Genre identification - improved to catch all genres
        genre_keywords = {
            "techno": ["techno", "minimal techno", "detroit techno"],
            "house": ["house", "deep house", "tech house", "progressive house"],
            "trance": ["trance", "uplifting trance", "progressive trance"],
            "hard dance": ["hard dance", "hardstyle", "hardcore"],
            "trap": ["trap", "future bass"],
            "mainstage": ["mainstage", "big room", "festival"],
            "drum and bass": ["drum and bass", "dnb", "jungle"],
            "dubstep": ["dubstep", "riddim", "melodic dubstep"]
        }
        
        for genre, keywords in genre_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                identified_genres.append(genre)
        
        # Energy/mood analysis
        if any(word in prompt_lower for word in ["hard", "intense", "peak", "banging"]):
            mood_requirements.extend(["high energy", "intense"])
        if any(word in prompt_lower for word in ["warm", "chill", "ambient", "downtempo"]):
            mood_requirements.extend(["warm", "chill"])
        if any(word in prompt_lower for word in ["dark", "underground", "warehouse"]):
            mood_requirements.extend(["dark", "underground"])
        
        # Create database query suggestions
        for genre in identified_genres:
            suggested_queries.append({"field": "genre", "operator": "ilike", "value": f"%{genre}%"})
        
        return {
            "identified_genres": identified_genres,
            "energy_requirements": {"level": "high" if "hard" in prompt_lower else "medium"},
            "mood_requirements": mood_requirements,
            "suggested_queries": suggested_queries
        }

class DurationAnalysisTool(BaseTool):
    name: str = "duration_quantity_analysis"
    description: str = "Extract duration and quantity requirements from user prompts"
    
    def _run(self, user_prompt: str, available_songs: int = 1000) -> Dict[str, Any]:
        """Extract time and quantity requirements"""
        logger.info(f"Analyzing duration/quantity for prompt: {user_prompt}")
        
        prompt_lower = user_prompt.lower()
        
        # Extract explicit numbers
        target_duration = None
        target_song_count = None
        
        # Look for duration mentions
        if "hour" in prompt_lower:
            if "2 hour" in prompt_lower or "two hour" in prompt_lower:
                target_duration = 120
            elif "1 hour" in prompt_lower or "one hour" in prompt_lower:
                target_duration = 60
            elif "3 hour" in prompt_lower or "three hour" in prompt_lower:
                target_duration = 180
        
        # Look for song count mentions
        import re
        numbers = re.findall(r'\b(\d+)\s*songs?\b', prompt_lower)
        if numbers:
            target_song_count = int(numbers[0])
        
        # Defaults if not specified
        if not target_duration and not target_song_count:
            target_song_count = 20  # Default playlist size
            target_duration = 60    # Default 1 hour
        elif target_duration and not target_song_count:
            # Estimate songs from duration (assuming 3-4 min per song + transitions)
            target_song_count = int(target_duration / 3.5)
        elif target_song_count and not target_duration:
            # Estimate duration from song count
            target_duration = target_song_count * 3.5
        
        transition_time_per_song = 0.5  # 30 seconds overlap/transition
        estimated_playtime = target_song_count * 3 + (target_song_count - 1) * transition_time_per_song
        
        return {
            "target_duration_minutes": target_duration,
            "target_song_count": target_song_count,
            "transition_time_per_song": transition_time_per_song,
            "estimated_playtime": estimated_playtime
        }

class SupervisorAgent:
    def __init__(self, llm_model: str = "gpt-4o-mini"):
        """Initialize the supervisor agent with LangChain tools"""
        self.llm = ChatOpenAI(
            model=llm_model,
            temperature=0.1,
            streaming=True
        )
        
        self.tools = [
            BPMKeyAnalysisTool(),
            TagAnalysisTool(),
            DurationAnalysisTool()
        ]
        
        self.prompt_template = ChatPromptTemplate.from_messages([
            ("system", """You are a professional DJ playlist generation expert. Your job is to analyze user requests 
            and coordinate with specialized tools to create the perfect playlist.
            
            Use the available tools to analyze:
            1. BPM progression, key compatibility, and energy flow
            2. Genre and tag requirements from the prompt
            3. Duration and song quantity requirements
            
            Combine the analyses to create a comprehensive query plan for the database.
            """),
            ("human", "{user_prompt}")
        ])
        
    def analyze_prompt(self, user_prompt: str) -> QueryPlan:
        """Analyze user prompt using sub-agent tools"""
        logger.info(f"Supervisor analyzing prompt: {user_prompt}")
        
        try:
            # Use tools to analyze different aspects
            bpm_tool = BPMKeyAnalysisTool()
            tag_tool = TagAnalysisTool()
            duration_tool = DurationAnalysisTool()
            
            bpm_analysis = bpm_tool._run(user_prompt)
            tag_analysis = tag_tool._run(user_prompt)
            duration_analysis = duration_tool._run(user_prompt)
            
            # Combine analyses into query plan
            query_plan = QueryPlan(
                genre_filters=tag_analysis["identified_genres"],
                bpm_range=bpm_analysis["bpm_range"],
                energy_requirements=bpm_analysis["energy_requirements"],
                target_song_count=duration_analysis["target_song_count"],
                set_template=bpm_analysis["set_template"],
                tag_filters={"mood": tag_analysis["mood_requirements"]}
            )
            
            logger.info(f"Generated query plan: {query_plan}")
            return query_plan
            
        except Exception as e:
            logger.error(f"Error in supervisor analysis: {e}")
            # Return default query plan
            return QueryPlan(
                genre_filters=[],
                bpm_range=(120, 130),
                energy_requirements={"min": 60, "max": 90},
                target_song_count=20,
                set_template="build_up_peak_cooldown"
            )