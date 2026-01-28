import json
import re
from pathlib import Path
from datetime import datetime

CHUNKER_VERSION = "1.1.0"

CAMPUS_NAMES = {
    'moscow': 'Москва',
    'spb': 'Санкт-Петербург', 
    'perm': 'Пермь',
    'nn': 'Нижний Новгород',
}

CONTENT_FIELDS = {
    'curriculum': ('what_to_study', 'Учебная программа'),
    'advantages': ('advantages', 'Преимущества программы'),
    'career': ('career', 'Карьера выпускников'),
    'admission': ('admission_info', 'Условия поступления'),
}

NOISE_PATTERNS = [
    r'Задать вопрос о программе.*$',
    r'Телеграм-канал для абитуриентов.*$',
    r'Подробнее на сайте.*$',
    r'\s{2,}',
]

def clean_text(text):
    if not text:
        return ''
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_program_header(program):
    campus = CAMPUS_NAMES.get(program['campus'], program['campus'])
    codes = program.get('codes', [])
    code_str = codes[0] if codes else ''
    
    header = f"Программа «{program['name']}»"
    if code_str:
        header += f" ({code_str})"
    header += f". {program['faculty']}, НИУ ВШЭ {campus}."
    return header

def create_overview_text(program):
    lines = [get_program_header(program), '']
    
    if program.get('duration'):
        lines.append(f"Срок обучения: {program['duration']}.")
    if program.get('form'):
        lines.append(f"Форма обучения: {program['form']}.")
    if program.get('language'):
        lang_map = {'RUS': 'русский', 'ENG': 'английский', 'RUS+ENG': 'русский и английский'}
        lines.append(f"Язык обучения: {lang_map.get(program['language'], program['language'])}.")
    if program.get('budget_places'):
        lines.append(f"Бюджетных мест: {program['budget_places']}.")
    if program.get('paid_places'):
        lines.append(f"Платных мест: {program['paid_places']}.")
    if program.get('exams'):
        exams_str = ', '.join([f"{e['subject']} (мин. {e['min_score']})" for e in program['exams']])
        lines.append(f"Вступительные экзамены: {exams_str}.")
    if program.get('specializations'):
        lines.append(f"Специализации: {', '.join(program['specializations'])}.")
    
    if program.get('description'):
        lines.append('')
        lines.append(clean_text(program['description']))
    
    return '\n'.join(lines)

def create_content_chunk_text(program, field_name, section_title):
    header = get_program_header(program)
    content = clean_text(program.get(field_name, ''))
    return f"{header}\n\n{section_title}:\n{content}"

def create_chunks(program):
    chunks = []
    campus = CAMPUS_NAMES.get(program['campus'], program['campus'])
    codes = program.get('codes', [])
    
    base_meta = {
        'program_slug': program['slug'],
        'program_name': program['name'],
        'program_code': codes[0] if codes else '',
        'faculty': program['faculty'],
        'campus': campus,
        'admission_year': program['admission_year'],
        'url': program['url'],
    }
    
    overview_text = create_overview_text(program)
    chunks.append({
        'chunk_id': f"{program['slug']}_overview",
        'chunk_type': 'overview',
        'text': overview_text,
        **base_meta
    })
    
    for chunk_type, (field_name, section_title) in CONTENT_FIELDS.items():
        text = program.get(field_name, '')
        if text and len(text) > 50:
            chunk_text = create_content_chunk_text(program, field_name, section_title)
            chunks.append({
                'chunk_id': f"{program['slug']}_{chunk_type}",
                'chunk_type': chunk_type,
                'text': chunk_text,
                **base_meta
            })
    
    return chunks

def process_programs(input_path, output_path):
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    with open(input_path, encoding='utf-8') as f:
        programs = json.load(f)
    
    all_chunks = []
    stats = {'overview': 0, 'curriculum': 0, 'advantages': 0, 'career': 0, 'admission': 0}
    text_lengths = []
    
    for program in programs:
        if program.get('status') == 'failed':
            continue
        
        chunks = create_chunks(program)
        all_chunks.extend(chunks)
        
        for chunk in chunks:
            stats[chunk['chunk_type']] += 1
            text_lengths.append(len(chunk['text']))
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
    
    avg_len = sum(text_lengths) / len(text_lengths) if text_lengths else 0
    min_len = min(text_lengths) if text_lengths else 0
    max_len = max(text_lengths) if text_lengths else 0
    
    manifest = {
        'chunker_version': CHUNKER_VERSION,
        'created_at': datetime.now().isoformat(),
        'input_file': str(input_path),
        'output_file': str(output_path),
        'total_programs': len(programs),
        'total_chunks': len(all_chunks),
        'chunks_by_type': stats,
        'text_length_stats': {
            'min': min_len,
            'max': max_len,
            'avg': round(avg_len, 1),
        }
    }
    
    manifest_path = output_path.parent / 'chunks_manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"CHUNKER v{CHUNKER_VERSION}")
    print(f"Input: {input_path}")
    print(f"Output: {output_path}")
    print(f"\nPrograms: {len(programs)}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"\nBy type:")
    for t, count in stats.items():
        print(f"  {t}: {count}")
    print(f"\nText length: min={min_len}, avg={avg_len:.0f}, max={max_len}")
    
    return all_chunks

if __name__ == '__main__':
    process_programs(
        'parser/data/moscow/all_programs.json',
        'rag/data/chunks_v1.jsonl'
    )
