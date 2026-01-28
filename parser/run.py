#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.program_parser import parse_all

parser = argparse.ArgumentParser()
parser.add_argument('--config', '-c', default='config/programs_moscow.json')
parser.add_argument('--output', '-o', default='data/moscow')
parser.add_argument('--limit', '-l', type=int)
args = parser.parse_args()

if not Path(args.config).exists():
    print(f"Ошибка: {args.config} не найден")
    sys.exit(1)

results = parse_all(args.config, args.output, args.limit)
n = len(results)

def stat(field):
    count = sum(1 for r in results if getattr(r, field))
    return f"{count}/{n} ({100*count//n}%)"

print(f"\n{'='*50}")
print(f"СТАТИСТИКА: {n} программ")
print(f"{'='*50}")
print(f"\nМета:")
print(f"  budget_places:    {stat('budget_places')}")
print(f"  paid_places:      {stat('paid_places')}")
print(f"  duration:         {stat('duration')}")
print(f"  form:             {stat('form')}")
print(f"  language:         {stat('language')}")
print(f"  exams:            {stat('exams')}")
print(f"  specializations:  {stat('specializations')}")
print(f"\nКонтент:")
print(f"  description:      {stat('description')}")
print(f"  what_to_study:    {stat('what_to_study')}")
print(f"  advantages:       {stat('advantages')}")
print(f"  career:           {stat('career')}")
print(f"  admission_info:   {stat('admission_info')}")
print(f"{'='*50}")
