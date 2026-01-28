import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from .fetch import download

PIPELINE_VERSION = "1.0.0"
MINKRIT_URL = 'https://ba.hse.ru/minkrit'
_minkrit_cache = None

REQUIRED_FIELDS = ['name', 'faculty', 'url', 'duration', 'form', 'language']
IMPORTANT_FIELDS = ['budget_places', 'exams', 'description']

def load_minkrit():
    global _minkrit_cache
    if _minkrit_cache is not None:
        return _minkrit_cache
    
    html = download(MINKRIT_URL)
    if not html:
        _minkrit_cache = {}
        return _minkrit_cache
    
    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    if len(tables) < 2:
        _minkrit_cache = {}
        return _minkrit_cache
    
    programs = {}
    current = None
    
    for row in tables[1].find_all('tr')[2:]:
        cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
        
        if len(cells) == 5:
            name = cells[1].replace('(онлайн)', '').replace('(реализуется на английском языке)', '').strip()
            current = name
            programs[name] = [{'subject': cells[2], 'min_score': int(cells[4])}]
        elif len(cells) == 3 and current:
            programs[current].append({'subject': cells[0], 'min_score': int(cells[2])})
    
    _minkrit_cache = programs
    return _minkrit_cache

def match_exams(program_name):
    minkrit = load_minkrit()
    
    def normalize(s):
        return re.sub(r'[^а-яёa-z0-9]', '', s.lower())
    
    name_norm = normalize(program_name)
    
    for mk_name, exams in minkrit.items():
        if normalize(mk_name) == name_norm:
            return exams
        if name_norm in normalize(mk_name) or normalize(mk_name) in name_norm:
            return exams
    
    words = [w for w in program_name.split() if len(w) > 3]
    for mk_name, exams in minkrit.items():
        mk_norm = normalize(mk_name)
        if sum(1 for w in words if normalize(w) in mk_norm) >= 2:
            return exams
    
    return None

@dataclass
class Program:
    slug: str = ""
    name: str = ""
    faculty: str = ""
    codes: list = field(default_factory=list)
    category: str = ""
    url: str = ""
    campus: str = ""
    admission_year: int = 2025
    retrieved_at: str = ""
    budget_places: int = None
    paid_places: int = None
    duration: str = ""
    form: str = ""
    language: str = ""
    exams: list = field(default_factory=list)
    description: str = ""
    what_to_study: str = ""
    advantages: str = ""
    career: str = ""
    admission_info: str = ""
    specializations: list = field(default_factory=list)
    status: str = "success"
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

def validate_program(p):
    errors = []
    warnings = []
    
    for f in REQUIRED_FIELDS:
        val = getattr(p, f)
        if not val:
            errors.append(f"missing_required:{f}")
    
    for f in IMPORTANT_FIELDS:
        val = getattr(p, f)
        if not val:
            warnings.append(f"missing_important:{f}")
    
    if errors:
        p.status = "failed"
    elif warnings:
        p.status = "partial"
    else:
        p.status = "success"
    
    p.errors = errors
    p.warnings = warnings
    return p

EXAM_NAMES = {
    'математика': 'Математика', 'русский язык': 'Русский язык',
    'информатика': 'Информатика', 'коммуникационные технологии': 'Информатика',
    'физика': 'Физика', 'химия': 'Химия', 'биология': 'Биология',
    'история': 'История', 'обществознание': 'Обществознание',
    'литература': 'Литература', 'иностранный язык': 'Иностранный язык',
    'английский язык': 'Иностранный язык', 'география': 'География',
}

SECTION_PATTERNS = {
    'what_to_study': ['что я буду изучать', 'изучать', 'о программе', 'кого и зачем', 
                      'во время обучения', 'процесс обучения', 'учебный план'],
    'advantages': ['преимущества', 'особенности', 'почему стоит'],
    'career': ['перспективы', 'карьер', 'после обучения', 'трудоустройство'],
    'admission_info': ['поступлен', 'нужно знать', 'как поступить', 'вступительн', 'егэ'],
}

def parse_page(html, config, campus="moscow", admission_year=2025):
    if isinstance(html, bytes):
        html = html.decode('utf-8', errors='replace')
    
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'noscript', 'nav', 'footer', 'header']):
        tag.decompose()
    
    p = Program(**{k: config.get(k, '' if k != 'codes' else []) 
                   for k in ['slug', 'name', 'faculty', 'codes', 'category', 'url']})
    p.campus = campus
    p.admission_year = admission_year
    p.retrieved_at = datetime.now().isoformat()
    
    text = soup.get_text(' ', strip=True)
    text_lower = text.lower()
    
    m = re.search(r'(\d+)\s*бюджетн', text)
    if m: p.budget_places = int(m.group(1))
    
    m = re.search(r'(\d+)\s*платн', text)
    if m: p.paid_places = int(m.group(1))
    
    m = re.search(r'(\d+)\s*(года?|лет)', text)
    if m:
        y = int(m.group(1))
        p.duration = f"{y} {'год' if y == 1 else 'года' if 2 <= y <= 4 else 'лет'}"
    
    for form in ['очно-заочная', 'заочная', 'очная']:
        if form in text_lower:
            p.form = form
            break
    
    if 'RUS+ENG' in text or ('русском' in text_lower and 'английском' in text_lower):
        p.language = 'RUS+ENG'
    elif 'ENG' in text or 'полностью на английском' in text_lower:
        p.language = 'ENG'
    else:
        p.language = 'RUS'
    
    h1 = soup.find('h1')
    if h1:
        for s in h1.find_next_siblings():
            if s.name in ['p', 'div']:
                t = s.get_text(' ', strip=True)
                if len(t) > 100:
                    p.description = re.sub(r'\s+', ' ', t).strip()
                    break
    
    for h2 in soup.find_all('h2'):
        title = h2.get_text(' ', strip=True).lower()
        if 'новости' in title or 'партнер' in title or 'каталог' in title:
            continue
        
        parts = []
        for s in h2.find_next_siblings():
            if s.name in ['h1', 'h2']:
                break
            t = s.get_text(' ', strip=True)
            if t:
                parts.append(t)
        content = re.sub(r'\s+', ' ', '\n'.join(parts)).strip()
        
        if len(content) < 50:
            continue
        
        for field_name, patterns in SECTION_PATTERNS.items():
            if not getattr(p, field_name) and any(pat in title for pat in patterns):
                setattr(p, field_name, content)
                break
    
    for m in re.finditer(r'([А-Яа-яёЁ][А-Яа-яёЁ\s\-]+)\s*\(минимальный балл[:\s]*(\d+)\)', text):
        subj = m.group(1).lower().strip()
        for k, v in EXAM_NAMES.items():
            if k in subj:
                if v not in [e['subject'] for e in p.exams]:
                    p.exams.append({'subject': v, 'min_score': int(m.group(2))})
                break
    
    if not p.exams:
        mk_exams = match_exams(p.name)
        if mk_exams:
            p.exams = mk_exams
    
    for a in soup.find_all('a', href=True):
        if '/spec_' in a['href'] or '/spec/' in a['href']:
            t = a.get_text(strip=True).strip('«»"\'')
            if 5 < len(t) < 100 and t.lower() not in ['о специализациях', 'общая информация']:
                if t not in p.specializations:
                    p.specializations.append(t)
    
    return validate_program(p)

def create_manifest(results, campus, admission_year, config_path, output_dir, started_at):
    success = [r for r in results if r.status == "success"]
    partial = [r for r in results if r.status == "partial"]
    failed = [r for r in results if r.status == "failed"]
    
    field_coverage = {}
    all_fields = ['budget_places', 'paid_places', 'duration', 'form', 'language', 
                  'exams', 'description', 'what_to_study', 'advantages', 'career', 
                  'admission_info', 'specializations']
    
    for f in all_fields:
        count = sum(1 for r in results if getattr(r, f))
        field_coverage[f] = {"count": count, "total": len(results), "percent": round(100 * count / len(results), 1)}
    
    manifest = {
        "pipeline_version": PIPELINE_VERSION,
        "created_at": datetime.now().isoformat(),
        "started_at": started_at,
        "config_path": str(config_path),
        "output_dir": str(output_dir),
        "campus": campus,
        "admission_year": admission_year,
        "statistics": {
            "total": len(results),
            "success": len(success),
            "partial": len(partial),
            "failed": len(failed),
            "source_types": {"html": len(results), "pdf": 0}
        },
        "field_coverage": field_coverage,
        "failed_programs": [{"slug": r.slug, "errors": r.errors} for r in failed],
        "partial_programs": [{"slug": r.slug, "warnings": r.warnings} for r in partial]
    }
    
    return manifest

def parse_all(config_path, output_dir, limit=None, admission_year=2025):
    started_at = datetime.now().isoformat()
    
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)
    
    campus = config.get('campus', 'moscow')
    programs = config.get('programs', [])
    
    if limit:
        programs = programs[:limit]
    
    out = Path(output_dir)
    (out / 'raw').mkdir(parents=True, exist_ok=True)
    (out / 'parsed').mkdir(parents=True, exist_ok=True)
    
    results = []
    download_failed = []
    
    for i, cfg in enumerate(programs):
        slug = cfg.get('slug', f'p{i}')
        print(f"[{i+1}/{len(programs)}] {slug}")
        
        html = download(cfg.get('url', ''))
        if not html:
            print(f"  DOWNLOAD_FAILED")
            download_failed.append(slug)
            continue
        
        (out / 'raw' / f'{slug}.html').write_bytes(html)
        
        p = parse_page(html, cfg, campus, admission_year)
        results.append(p)
        
        (out / 'parsed' / f'{slug}.json').write_text(
            json.dumps(asdict(p), ensure_ascii=False, indent=2), encoding='utf-8')
        
        status_icon = {"success": "✓", "partial": "~", "failed": "✗"}[p.status]
        print(f"  {status_icon} {p.status}: {p.budget_places} бюджет")
    
    (out / 'all_programs.json').write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2), encoding='utf-8')
    
    manifest = create_manifest(results, campus, admission_year, config_path, output_dir, started_at)
    manifest["download_failed"] = download_failed
    
    (out / 'manifest.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    
    print(f"\n{'='*50}")
    print(f"PIPELINE v{PIPELINE_VERSION} COMPLETED")
    print(f"{'='*50}")
    print(f"Total: {manifest['statistics']['total']}")
    print(f"  ✓ Success: {manifest['statistics']['success']}")
    print(f"  ~ Partial: {manifest['statistics']['partial']}")
    print(f"  ✗ Failed:  {manifest['statistics']['failed']}")
    if download_failed:
        print(f"  ⚠ Download failed: {len(download_failed)}")
    print(f"{'='*50}")
    
    return results

if __name__ == '__main__':
    parse_all('config/programs_moscow.json', 'data/moscow')
