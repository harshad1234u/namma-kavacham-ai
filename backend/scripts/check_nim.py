"""Check the configured NVIDIA NIM endpoint: Sarvam-M chat and Nemotron embeddings.

Usage (from backend/, with AI_ENABLED=true and NVIDIA_NIM_API_KEY set in .env or the environment):
    python scripts/check_nim.py
Prints only model ids and pass/fail reasons; never the API key.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.civic.nim.provider import NIMError, build_chat, build_embedder  # noqa: E402
from app.civic.settings import CivicSettings  # noqa: E402


async def main() -> int:
    s = CivicSettings()
    print(f"endpoint:  {s.nvidia_nim_base_url}")
    print(f"ai_active: {s.ai_active}  (needs AI_ENABLED=true and NVIDIA_NIM_API_KEY)")
    if not s.ai_active:
        return 1
    ok = True
    chat, emb = build_chat(s), build_embedder(s)
    try:
        out = await chat.chat_json("Return JSON only.", 'Reply with {"ok": true} and translate "farmer" to Hindi as "hi".',
                                   {"type": "object", "properties": {"ok": {"type": "boolean"}, "hi": {"type": "string"}},
                                    "required": ["ok", "hi"]}, max_tokens=200)
        print(f"chat  {chat.model}: OK -> {out}")
    except NIMError as exc:
        ok = False
        print(f"chat  {chat.model}: FAILED ({exc.reason})")
    try:
        vec = (await emb.embed(["PM-KISAN income support"], "query"))[0]
        print(f"embed {emb.model}: OK -> dimension {len(vec)}")
    except NIMError as exc:
        ok = False
        print(f"embed {emb.model}: FAILED ({exc.reason})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
