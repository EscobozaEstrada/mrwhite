#!/usr/bin/env python3
"""
Verify book indexing in Pinecone
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
script_dir = Path(__file__).parent
env_local = script_dir.parent / ".env.local"
env_parent = script_dir.parent.parent / ".env"

if env_local.exists():
    load_dotenv(env_local)
else:
    load_dotenv(env_parent)

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.pinecone_client import PineconeClient
from config.settings import settings

def main():
    print("=" * 70)
    print("📊 PINECONE INDEX VERIFICATION")
    print("=" * 70)
    
    pc = PineconeClient()
    stats = pc.index.describe_index_stats()
    
    print(f"\n📈 Index: {pc.index_name}")
    print(f"   Total vectors: {stats.total_vector_count:,}")
    print(f"   Dimension: {stats.dimension}")
    
    print(f"\n📁 Namespaces ({len(stats.namespaces)}):")
    for ns, ns_stats in sorted(stats.namespaces.items()):
        print(f"   - {ns}: {ns_stats.vector_count:,} vectors")
    
    # Check for book namespace
    book_ns = f"book-content-{settings.ENVIRONMENT}"
    if book_ns in stats.namespaces:
        book_count = stats.namespaces[book_ns].vector_count
        print(f"\n✅ Book namespace found: {book_ns} ({book_count} vectors)")
    else:
        print(f"\n❌ Book namespace NOT found: {book_ns}")
    
    print("=" * 70)

if __name__ == "__main__":
    main()

