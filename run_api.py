"""Start the existing, integrity-checked local API; no notebook execution."""
import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    # Unified local tree is the default; an explicit storage override remains authoritative.
    os.environ.setdefault('DISEASE_API_STORAGE_ROOT', str(Path(__file__).resolve().parent))
    import uvicorn
    uvicorn.run('app.backend.main:app', host='127.0.0.1', port=args.port,
                workers=1, reload=False)


if __name__ == '__main__':
    main()
