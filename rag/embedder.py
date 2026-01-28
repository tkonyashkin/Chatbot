import json
import numpy as np
from pathlib import Path
from datetime import datetime
from sentence_transformers import SentenceTransformer

EMBEDDER_VERSION = "1.0.0"
MODEL_NAME = "intfloat/multilingual-e5-large"

def load_chunks(chunks_path):
    chunks = []
    with open(chunks_path, 'r', encoding='utf-8') as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks

def embed_chunks(chunks_path, output_dir, batch_size=32):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)
    
    print(f"Loading chunks from {chunks_path}")
    chunks = load_chunks(chunks_path)
    
    texts = []
    for chunk in chunks:
        text = f"passage: {chunk['text']}"
        texts.append(text)
    
    print(f"Embedding {len(texts)} chunks (batch_size={batch_size})")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    
    embeddings_path = output_dir / 'embeddings.npy'
    np.save(embeddings_path, embeddings)
    print(f"Saved embeddings to {embeddings_path}")
    
    chunks_meta_path = output_dir / 'chunks_metadata.jsonl'
    with open(chunks_meta_path, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(chunks):
            chunk_meta = {
                'idx': i,
                'chunk_id': chunk['chunk_id'],
                'chunk_type': chunk['chunk_type'],
                'program_slug': chunk['program_slug'],
                'program_name': chunk['program_name'],
                'program_code': chunk['program_code'],
                'faculty': chunk['faculty'],
                'campus': chunk['campus'],
                'admission_year': chunk['admission_year'],
                'url': chunk['url'],
                'text': chunk['text']
            }
            f.write(json.dumps(chunk_meta, ensure_ascii=False) + '\n')
    print(f"Saved metadata to {chunks_meta_path}")
    
    manifest = {
        'embedder_version': EMBEDDER_VERSION,
        'model_name': MODEL_NAME,
        'created_at': datetime.now().isoformat(),
        'input_file': str(chunks_path),
        'output_dir': str(output_dir),
        'total_chunks': len(chunks),
        'embedding_dim': embeddings.shape[1],
        'batch_size': batch_size,
    }
    
    manifest_path = output_dir / 'embeddings_manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    print(f"\nEMBEDDER v{EMBEDDER_VERSION}")
    print(f"Model: {MODEL_NAME}")
    print(f"Total chunks: {len(chunks)}")
    print(f"Embedding dim: {embeddings.shape[1]}")
    print(f"Output: {output_dir}")
    
    return embeddings, chunks

if __name__ == '__main__':
    embed_chunks(
        'rag/data/chunks_v1.jsonl',
        'rag/data/embeddings'
    )
