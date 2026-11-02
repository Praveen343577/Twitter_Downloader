#!/usr/bin/env python3
import sys
from pathlib import Path

def deduplicate(input_path: str, output_path: str) -> None:
    seen = set()
    with open(input_path, 'r', encoding='utf-8', errors='replace') as infile, \
         open(output_path, 'w', encoding='utf-8') as outfile:
        for line in infile:
            clean_line = line.strip()
            if clean_line and clean_line not in seen:
                seen.add(clean_line)
                outfile.write(clean_line + '\n')

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(f"Usage: {sys.argv[0]} <input.txt> <output.txt>")
    deduplicate(sys.argv[1], sys.argv[2])