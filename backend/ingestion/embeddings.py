"""Backfill description embeddings for books missing vectors."""
from typing import List
from tqdm import tqdm
from sqlalchemy import func, select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from clients.openai_client import OpenAIClient
from db.stores.book_store import BookStore
from db.schema import BookModel

def embedding_text(book: dict) -> str:
    """Canonical text used for book description embeddings."""
    return f"{book['title']}\n\n{book['description']}"

async def update_book_embedding(
    isbn13: str,
    embedding: list[float],
    session: AsyncSession,
) -> None:
    stmt = (
        update(BookModel)
        .where(BookModel.isbn13 == isbn13)
        .values(embedding=embedding)
    )
    await session.execute(stmt)


async def embed_missing_books(
    session_factory: async_sessionmaker[AsyncSession],
    openai_client: OpenAIClient,
) -> int:
    """Backfill embeddings for rows where embedding IS NULL."""
    
    async with session_factory() as session:
        book_store = BookStore(session)
        num_missing = await book_store.get_num_book_missing_embeddings()
        if num_missing == 0:
            print("No books missing embeddings")
            return 0
        
        batch_isbn13 = []
        batch_text = []
        books = await book_store.get_missing_embeddings()
        count = 0
        token_count = 0
        for book in books:
            text = embedding_text(book)
            
            if openai_client.over_max_tokens(token_count + openai_client.token_count(text)):
                embeddings = await openai_client.get_embeddings_batch(batch_text)
                for i, embedding in enumerate(embeddings):
                    await update_book_embedding(batch_isbn13[i], embedding, session)
                
                await session.commit()
                
                count += len(batch_isbn13)
                print(f"✅ BATCH: Embedded {len(batch_isbn13)} books")
                
                batch_isbn13 = []
                batch_text = []
                token_count = 0
                
            batch_isbn13.append(book["isbn13"])
            batch_text.append(text)
            token_count += openai_client.token_count(text)
            
        if len(batch_isbn13) > 0:
            embeddings = await openai_client.get_embeddings_batch(batch_text)
            for i, embedding in enumerate(embeddings):
                await update_book_embedding(batch_isbn13[i], embedding, session)
                
            await session.commit()
            
            count += len(batch_isbn13)
            print(f"✅ FINAL LEFT OVER: Embedded {count} books")

        print(f"✅ Embedded {len(books)} books")
        return len(books)
