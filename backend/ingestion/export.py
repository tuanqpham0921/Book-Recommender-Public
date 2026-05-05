#!/usr/bin/env python3
import sys
import json
import asyncio

from datetime import datetime, UTC

from app.db.redis import init_redis, close_redis


async def export_specific_chats(chat_ids, output_file="default.json"):
    """Export specific chat IDs to JSON file"""
    print(f"Exporting {len(chat_ids)} specific chats to {output_file}")

    # Initialize Redis connection
    rdb = await init_redis()
    if not rdb:
        print("❌ Failed to connect to Redis")
        return []

    try:
        exported_chats = []

        for chat_id in chat_ids:
            try:
                # Get full chat key
                chat_key = f"chat:{chat_id}"
                chat_data = await rdb.json().get(chat_key)

                if chat_data:
                    # Convert timestamps to ISO format
                    if "created" in chat_data:
                        chat_data["created"] = datetime.fromtimestamp(
                            chat_data["created"], tz=UTC
                        ).isoformat()

                    if "messages" in chat_data:
                        for message in chat_data["messages"]:
                            if "created" in message:
                                message["created"] = datetime.fromtimestamp(
                                    message["created"], tz=UTC
                                ).isoformat()

                    exported_chats.append(chat_data)
                    print(f"✓ Exported chat: {chat_id}")
                else:
                    print(f"✗ Chat not found: {chat_id}")

            except Exception as e:
                print(f"✗ Error exporting chat {chat_id}: {e}")

        # Write to JSON file
        with open(f"log/{output_file}", "w") as f:
            json.dump(exported_chats, f, indent=2)

        print(f"\n{len(exported_chats)} chats exported to {output_file}")
        return exported_chats

    finally:
        # Always close Redis connection
        await close_redis()


async def list_all_chat_ids():
    """List all available chat IDs"""
    # Initialize Redis connection
    rdb = await init_redis()
    if not rdb:
        print("❌ Failed to connect to Redis")
        return []

    try:
        # Get all chat keys
        keys = await rdb.keys("chat:*")
        chat_ids = [key.replace("chat:", "") for key in keys]

        print("Available chat IDs:")
        for chat_id in chat_ids:
            print(f"  - {chat_id}")

        return chat_ids

    finally:
        # Always close Redis connection
        await close_redis()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(
            "  python export_specific_chats.py list                    # List all chat IDs"
        )
        print(
            "  python export_specific_chats.py <chat_id1> [chat_id2...]  # Export specific chats"
        )
        print(
            "  python export_specific_chats.py all                     # Export all chats"
        )
        return

    if sys.argv[1] == "list":
        asyncio.run(list_all_chat_ids())
    else:
        # Export specific chat IDs
        chat_ids = sys.argv[1:]
        output_file = f"chats_{'_'.join(chat_ids)}.json"
        asyncio.run(export_specific_chats(chat_ids, output_file))


if __name__ == "__main__":
    main()
