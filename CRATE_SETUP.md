# DJroid Crate Command Setup Guide

## Implementation Status

✅ **COMPLETED:**
- CLI command interface updated to match documentation spec
- LangChain-based agent system with supervisor and sub-agents
- Enhanced database models with `popularimeter` field for energy ratings
- Enhanced SongDAO with advanced search capabilities
- M3U and Rekordbox XML playlist generators
- Intelligent song organization by DJ set templates
- Comprehensive error handling and user feedback

## Setup Requirements

### 1. Virtual Environment Setup
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies
```bash
# Install the package in development mode
pip install -e .

# This will install all dependencies from pyproject.toml including:
# - LangChain ecosystem (langchain-openai, langchain-core, etc.)
# - Database dependencies (SQLAlchemy, psycopg2-binary)
# - CLI dependencies (click, rich)
```

### 3. Environment Configuration
```bash
# Set OpenAI API key for LangChain agents
export OPENAI_API_KEY="your-openai-api-key-here"

# Optional: Configure database if not using default
export DATABASE_URL="postgresql://user:pass@localhost/djroid"
```

### 4. Database Migration (if needed)
Since we added the `popularimeter` field to the Song model, you may need to run a database migration:

```python
# Create a migration script or manually add the column:
ALTER TABLE songs ADD COLUMN popularimeter INTEGER;
CREATE INDEX ix_songs_popularimeter ON songs (popularimeter);
```

## Usage Examples

### Basic M3U Playlist
```bash
djroid crate "give me 20 techno songs for peak time"
```

### Rekordbox XML for USB Export
```bash
djroid --path /Users/dj/USB --usb crate "build a 2-hour progressive house set"
```

### With Custom Output Path
```bash
djroid --path /Users/dj/Playlists crate "hard dance warmup set for festival"
```

## Architecture Overview

### Command Flow
1. **CLI** (`cli.py`) → Parses arguments and calls service
2. **Service** (`crate.py`) → Orchestrates the entire process
3. **LLM Agents** (`agents.py`) → Analyze user prompt using LangChain
4. **Database** (`song_dao.py`) → Query songs with enhanced search
5. **Organization** (`playlist_generators.py`) → Organize by DJ set templates
6. **Output** → Generate M3U or Rekordbox XML files

### LangChain Agent System
- **SupervisorAgent**: Coordinates analysis and creates query plans
- **BPMKeyAnalysisTool**: Analyzes BPM progression and key compatibility
- **TagAnalysisTool**: Maps prompts to database tag queries
- **DurationAnalysisTool**: Extracts time and quantity requirements

### Set Templates
- `build_up_peak_cooldown`: Classic DJ structure (default)
- `constantly_building`: For hard dance/techno
- `peak_sustain_peak`: For mainstream sets
- `gradual_build`: For ambient/progressive

### Camelot Wheel Integration
Automatic key compatibility using Camelot notation for harmonic mixing.

## Testing the Implementation

### Quick Test (without full setup)
```bash
python3 test_crate_implementation.py
```

### Full Integration Test
```bash
# After completing setup steps 1-3 above
djroid crate "give me 5 house songs"
```

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Ensure virtual environment is activated and dependencies installed
2. **OpenAI API errors**: Check OPENAI_API_KEY environment variable
3. **Database errors**: Ensure database is running and accessible
4. **No songs found**: Check that songs are scanned into database with `djroid scan`

### Debug Mode
Add logging configuration to see detailed execution:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## File Structure
```
djroid/
├── cli/cli.py              # Updated CLI with new crate command
├── services/crate.py       # Main orchestration service
├── llm/
│   ├── agents.py          # LangChain-based agent system
│   └── playlist_generators.py  # M3U and XML generators
├── db/
│   ├── models/song.py     # Updated with popularimeter field
│   └── dao/song_dao.py    # Enhanced search capabilities
```

## Next Steps for Production

1. **Enhanced Tag Schema**: Implement more sophisticated tag matching
2. **Key Analysis**: Add actual audio analysis for key detection
3. **BPM Detection**: Integrate with audio analysis libraries
4. **Machine Learning**: Add recommendation algorithms based on listening history
5. **Batch Processing**: Support for multiple playlists generation
6. **Web Interface**: Add web UI for easier playlist creation

The implementation follows LangChain best practices and provides a solid foundation for AI-powered DJ playlist generation.