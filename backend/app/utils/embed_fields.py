#!/usr/bin/env -S poetry run python

import asyncio
import os
import asyncpg
from openai import AsyncOpenAI
import re, unicodedata
from app.db.postgres import init_postgres, close_postgres

import re, unicodedata, pykakasi
from pypinyin import lazy_pinyin

kks = pykakasi.kakasi()

from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)
EMBEDDING_MODEL = "text-embedding-3-large"
EMBED_DIM = 1024


async def get_postgres_client():
    return await init_postgres()


def romanize_if_needed(name: str) -> str:
    if re.search(r"[\u4E00-\u9FFF]", name):
        # CJK Unified Ideographs
        converted = kks.convert(name)
        if converted:
            return " ".join([item["hepburn"].capitalize() for item in converted])
        else:
            return " ".join(lazy_pinyin(name))

    return name


def normalize_author(name: str) -> str:
    name = name.strip()
    name = unicodedata.normalize("NFKC", name)
    name = re.sub(r";", " ", name).strip()

    ascii_only = re.sub(r"[^a-zA-Z0-9\s]", " ", name)
    ascii_only = re.sub(r"\s+", " ", ascii_only).strip()

    return name

    # if ascii_only:
    #     return ascii_only
    # romanized = romanize_if_needed(name)
    # if romanized:
    #     print(f"Converted '{name}' to '{romanized}'")

    # return romanized or name


async def embed_authors():
    conn = await get_postgres_client()

    rows = await conn.fetch(
        """
        SELECT DISTINCT authors FROM books
        WHERE authors IS NOT NULL AND authors <> '';
    """
    )

    for row in rows:
        author = row["authors"]
        norm = normalize_author(author)

        if not norm:
            print(f"Skipping empty author name for original '{author}'")
            continue
        print(f"Embedding author: {author} -> '{norm}'")

        # Create embedding
        response = await client.embeddings.create(model=EMBEDDING_MODEL, input=norm)
        emb = response.data[0].embedding

        # Update all books with this author's embedding
        await conn.execute(
            """
            UPDATE books
            SET author_embedding = $1
            WHERE authors = $2;
        """,
            emb,
            author,
        )

        print(f"Embedded: {author}")

    await conn.close()


if __name__ == "__main__":
    asyncio.run(embed_authors())
