"""Rebuild edits from explicitly supplied native source evidence.

Old dataset/archive-only invocation is retired; no cached augmented poses are used.
"""
from motion_edit.generation.regenerate_edits import main


if __name__ == "__main__":
    main()
