from typing import Any, List

import json, random, yaml
from collections import Counter


def load_json(filepath: str) -> Any:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(e)
        return None


def load_yaml(filepath: str) -> Any:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(e)
        return None


def display_status_code_stats(status_codes: List[int]) -> None:
    status_count = Counter(status_codes)

    for status, count in status_count.items():
        print(f"{status}: {count}")


def use_proxy_func(current_value: bool, alpha: float) -> bool:
    if current_value is False:
        return True
    else:
        return random.random() < alpha


def select_weighted_value(
    values: List[Any],
    weights: List[float],
) -> Any:
    if len(values) != len(weights):
        raise ValueError("Values and weights must have the same length")

    return random.choices(values, weights=weights, k=1)[0]