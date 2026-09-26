"""In-memory request store, seeded with the synthetic demo requests.

ponytail: process memory only - new reports vanish on restart and are not shared between instances;
swap for a database table when this leaves demo mode.
"""
import threading
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from app.civic.development.data import load_dev_data

MAX_REQUESTS = 5000


@dataclass
class StoredRequest:
    id: str
    text: str  # PII-minimised; never returned by aggregate endpoints
    language: str
    category: str
    issue_type: str | None
    area_id: str | None  # demo area, or None for places outside the demo dataset
    state: str
    district: str
    locality: str | None
    urgency: str
    source: str
    created_at: date
    scheme_ids: list[str] = field(default_factory=list)
    photo_attached: bool = False
    demo: bool = False


class RequestStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: list[StoredRequest] = []

    def seed(self) -> None:
        from app.civic.development.classifier import classify_deterministic
        from app.civic.schemes.identify import identify_schemes

        data = load_dev_data()
        rows = []
        for r in data.seed_requests:
            a = data.area(r.area_id)
            issue = classify_deterministic(r.text, r.category).issue_type
            rows.append(StoredRequest(r.id, r.text, r.language, r.category, issue, r.area_id, a.state, a.district, a.area,
                                      r.urgency, r.source, r.created_at, [m.scheme_id for m in identify_schemes(r.text)], demo=True))
        with self._lock:
            self._items = rows

    def add(self, req: StoredRequest) -> StoredRequest:
        with self._lock:
            if len(self._items) >= MAX_REQUESTS:
                # drop the oldest citizen-submitted report, never the demo seed
                idx = next((i for i, x in enumerate(self._items) if not x.demo), None)
                if idx is None:
                    raise OverflowError("store full")
                self._items.pop(idx)
            self._items.append(req)
        return req

    def all(self) -> list[StoredRequest]:
        with self._lock:
            return list(self._items)

    def get_many(self, ids: list[str]) -> list[StoredRequest]:
        wanted = set(ids)
        return [r for r in self.all() if r.id in wanted]


def new_id() -> str:
    return "REQ-" + uuid.uuid4().hex[:12].upper()


def today() -> date:
    return datetime.now(timezone.utc).date()


_store: RequestStore | None = None


def get_store() -> RequestStore:
    global _store
    if _store is None:
        _store = RequestStore()
        _store.seed()
    return _store
