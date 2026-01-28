#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.program_parser import parse_all, PIPELINE_VERSION

parser = argparse.ArgumentParser(description=f'HSE Parser v{PIPELINE_VERSION}')
parser.add_argument('--config', '-c', default='config/programs_moscow.json')
parser.add_argument('--output', '-o', default='data/moscow')
parser.add_argument('--limit', '-l', type=int)
parser.add_argument('--year', '-y', type=int, default=2025)
args = parser.parse_args()

if not Path(args.config).exists():
    print(f"Ошибка: {args.config} не найден")
    sys.exit(1)

print(f"HSE Bachelor Programs Parser v{PIPELINE_VERSION}")
print(f"Config: {args.config}")
print(f"Output: {args.output}")
print(f"Admission year: {args.year}")
print()

results = parse_all(args.config, args.output, args.limit, args.year)

manifest_path = Path(args.output) / 'manifest.json'
print(f"\nManifest: {manifest_path}")
print("Dataset is ready" if manifest_path.exists() else "Dataset is not ready")
