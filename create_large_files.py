"""Generate large text files with many lines for testing.

Usage:
    python3 create_large_files.py --count 1 --lines 300000 --prefix large_file_

This script writes files incrementally to avoid using too much memory.
"""

import argparse


def generate_file(path, lines):
    with open(path, 'w', encoding='utf-8') as f:
        for i in range(1, lines + 1):
            f.write(f"# This is line {i}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=1, help='How many files to create')
    parser.add_argument('--lines', type=int, default=300000, help='Lines per file')
    parser.add_argument('--prefix', type=str, default='large_file_', help='Filename prefix')
    args = parser.parse_args()

    for idx in range(1, args.count + 1):
        filename = f"{args.prefix}{idx}.txt"
        print(f"Generating {filename} with {args.lines} lines...")
        generate_file(filename, args.lines)
        print(f"Done: {filename}")


if __name__ == '__main__':
    main()
