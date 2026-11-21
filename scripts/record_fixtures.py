"""Record real arXiv and Wikipedia responses for the queries in fixtures/manifest.json.

Requests go through core.tools so the 3 second arXiv delay applies. Bodies are
stored in fixtures/responses.json under the key core.tools uses in OFFLINE mode.
"""

import json
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core import tools  # noqa: E402


def main() -> None:
    manifest = json.loads((REPO / "fixtures" / "manifest.json").read_text())
    recorded: dict[str, str] = {}
    real_get = requests.get

    def recording_get(url, params=None, **kwargs):
        resp = real_get(url, params=params, **kwargs)
        print(resp.status_code, tools._offline_key(url, params))
        recorded[tools._offline_key(url, params)] = resp.text
        return resp

    tools.requests.get = recording_get

    for query in manifest["arxiv_searches"]:
        tools.reset_cache()
        tools.search_arxiv(query)
    for paper_id in manifest["arxiv_abstract_ids"]:
        tools.reset_cache()
        tools.get_abstract(paper_id)
    for term in manifest["wikipedia_terms"]:
        tools.lookup_wikipedia(term)

    out = REPO / "fixtures" / "responses.json"
    out.write_text(json.dumps(recorded, indent=1, sort_keys=True) + "\n")
    print(f"wrote {len(recorded)} responses to {out}")


if __name__ == "__main__":
    main()
