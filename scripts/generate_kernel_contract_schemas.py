"""Backward-compatibility shim. Use generate_repository_schemas.py instead.

This script was renamed to generate_repository_schemas.py in the pre-1.0
public-release cleanup pass. It delegates to the new script unchanged.
"""

from generate_repository_schemas import main

if __name__ == "__main__":
    main()
