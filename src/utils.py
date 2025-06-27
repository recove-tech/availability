from typing import Any, List, Dict

import json
from collections import Counter


def load_json(filepath: str) -> Any:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(e)
        return None


def display_status_code_stats(status_codes: List[int]) -> None:
    status_count = Counter(status_codes)

    for status, count in status_count.items():
        print(f"{status}: {count}")
