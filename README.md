# DJroid

A powerful music library management tool for DJs, built with Python and PostgreSQL.

## Features

- Music file ingestion with metadata extraction
- Playlist management
- Tag-based organization
- BPM and key tracking
- Modern database design with SQLAlchemy

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/djroid.git
cd djroid
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

4. Set up PostgreSQL:
- Install PostgreSQL if you haven't already
- Create a database named 'djroid'
- Update the `.env` file with your database URL if needed

## Usage

Initialize the database:
```bash
djroid init
```

Ingest music files:
```bash
djroid ingest /path/to/music/directory
```

## Development

To set up the development environment:

1. Install development dependencies:
```bash
pip install -e ".[dev]"
```

2. Run tests:
```bash
pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 