#!/usr/bin/env python3
"""Preia confirmările primite și le scrie în data.json, pentru tabelul privat.

Rulează în GitHub Actions la fiecare 10 minute. Nu depinde de niciun calculator
personal. Confirmările deja salvate se păstrează: fișierul e reconstruit din
tot ce s-a primit, deduplicat după identificatorul cererii.
"""

import json
import urllib.request
from pathlib import Path

INBOX_ID = "3bde53e0-d039-4295-a156-3149658870a3"
API = f"https://webhook.site/token/{INBOX_ID}/requests?sorting=oldest&per_page=100"
OUT = Path(__file__).resolve().parent.parent / "data.json"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "botez-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def clamp(value):
    try:
        n = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(n, 30))


def main():
    existing = {}
    if OUT.exists():
        for item in json.loads(OUT.read_text(encoding="utf-8")).get("confirmari", []):
            existing[item.get("id")] = item

    requests = []
    page = 1
    while page <= 20:  # 100 pe pagina => plafon de 2000 de confirmari
        payload = get(f"{API}&page={page}")
        batch = payload.get("data", [])
        requests.extend(batch)
        if payload.get("is_last_page") or not batch:
            break
        page += 1

    for req in requests:
        rid = req.get("uuid")
        if not rid or rid in existing:
            continue
        try:
            body = json.loads(req.get("content") or "{}")
        except json.JSONDecodeError:
            continue

        name = str(body.get("name", "")).strip().replace("\n", " ")[:80]
        adults = clamp(body.get("adults"))
        kids = clamp(body.get("kids"))
        if len(name) < 2 or adults + kids < 1:
            continue

        existing[rid] = {
            "id": rid,
            "nume": name,
            "adulti": adults,
            "copii": kids,
            "total": adults + kids,
            "trimis": body.get("at") or req.get("created_at"),
        }

    rows = sorted(existing.values(), key=lambda r: r.get("trimis") or "")
    data = {
        "actualizat": __import__("datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "total_adulti": sum(r["adulti"] for r in rows),
        "total_copii": sum(r["copii"] for r in rows),
        "total_persoane": sum(r["total"] for r in rows),
        "confirmari": rows,
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} confirmări, {data['total_persoane']} persoane")


if __name__ == "__main__":
    main()
