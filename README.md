# dj-en

(Disk Jockey Etymological Network) A powerful music library management tool for DJs, built with Python and PostgreSQL.

## Features

- Music file ingestion with metadata extraction
- Playlist management
- Tag-based organization
- BPM and key tracking
- Metadata-based file migration
- Modern database design with SQLAlchemy

## Installation

1. Clone the repository:
```bash
git clone https://github.com/Moth-Man/dj-en.git
cd dj-en
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
- Create a database named 'dj_en_dev'
- Update the `.env` file with your database URL if needed

## Usage

Launch the TUI:
```bash
dj-en
```

Scan music files:
```bash
dj-en scan /path/to/music/directory
```

Migrate files based on metadata rules:
```bash
dj-en migrate
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
