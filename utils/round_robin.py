from collections import defaultdict, deque
from typing import List, Dict, Any


def round_robin(items: List[Any], key: str) -> List[Any]:
    """
    Interleave items by attribute `key` in round-robin order.
    Preserves relative order within each group.
    """

    buckets: dict[str, deque] = defaultdict(deque)

    for item in items:
        buckets[getattr(item, key)].append(item)

    result: List[Any] = []

    while buckets:
        empty = []

        for k, q in buckets.items():
            if q:
                result.append(q.popleft())
            if not q:
                empty.append(k)

        for k in empty:
            del buckets[k]

    return result
