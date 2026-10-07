"""Local-first notification inbox, prioritization, and lifecycle management."""
from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Mapping

from core.user_paths import get_user_data_dir

_URGENCY_TIERS = {
    "critical": "Now",
    "high": "Today",
    "normal": "This Week",
    "low": "FYI",
}
_TIER_RANK = {"Now": 0, "Today": 1, "This Week": 2, "FYI": 3, "Mute": 4}
_VALID_URGENCY = frozenset(_URGENCY_TIERS)


@dataclass(frozen=True)
class NotificationEvent:
    source: str
    event_type: str
    title: str
    body: str = ""
    urgency: str = "normal"
    entity: str = ""
    deadline: str | None = None
    sentiment: str = "neutral"
    dedupe_key: str | None = None
    created_at: str | None = None
    sensitive: bool = False


@dataclass(frozen=True)
class StoredNotification:
    id: int
    dedupe_key: str
    source: str
    event_type: str
    title: str
    body: str
    urgency: str
    entity: str
    deadline: str | None
    sentiment: str
    created_at: str
    priority: str
    status: str
    snoozed_until: str | None


def _parse_datetime(value: str | datetime) -> datetime:
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class NotificationBrain:
    """Persist and rank notification events without storing credentials.

    ``source_rules`` maps source names to urgency levels (or ``"mute"``).
    ``vip_entities`` are case-insensitive exact entity names. Quiet hours use
    local wall-clock time; priority ``Now`` notifications bypass them.
    """

    def __init__(
        self,
        db_path: Path | str | None = None,
        source_rules: Mapping[str, str] | None = None,
        vip_entities: set[str] | None = None,
        quiet_hours: tuple[str, str] | None = None,
    ):
        self.db_path = Path(db_path) if db_path else get_user_data_dir() / "notifications.sqlite3"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.source_rules = {
            str(source).strip().casefold(): str(rule).strip().casefold()
            for source, rule in (source_rules or {}).items()
        }
        self.vip_entities = {str(entity).strip().casefold() for entity in (vip_entities or set())}
        self.quiet_hours = quiet_hours
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY,
                    dedupe_key TEXT NOT NULL UNIQUE,
                    source TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    urgency TEXT NOT NULL,
                    entity TEXT NOT NULL,
                    deadline TEXT,
                    sentiment TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    snoozed_until TEXT
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS notifications_created_at_idx "
                "ON notifications(created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS notifications_status_idx "
                "ON notifications(status, snoozed_until)"
            )

    def priority(self, event: NotificationEvent, now: datetime | None = None) -> str:
        urgency = str(event.urgency).strip().casefold()
        if urgency not in _VALID_URGENCY:
            raise ValueError(f"Unsupported urgency: {event.urgency}")
        rule = self.source_rules.get(event.source.strip().casefold())
        if rule == "mute":
            return "Mute"
        if rule in _VALID_URGENCY:
            urgency = rule
        tier = _URGENCY_TIERS[urgency]

        reference = _parse_datetime(now or datetime.now().astimezone())
        if event.deadline:
            remaining = _parse_datetime(event.deadline) - reference
            if remaining <= timedelta(hours=6):
                tier = "Now"
            elif remaining <= timedelta(hours=24):
                tier = min((tier, "Today"), key=_TIER_RANK.get)
            elif remaining <= timedelta(days=7):
                tier = min((tier, "This Week"), key=_TIER_RANK.get)

        if event.entity.strip().casefold() in self.vip_entities:
            tier = min((tier, "Today"), key=_TIER_RANK.get)
        return tier

    def is_quiet(self, now: datetime | None = None) -> bool:
        if not self.quiet_hours:
            return False
        start = time.fromisoformat(self.quiet_hours[0])
        end = time.fromisoformat(self.quiet_hours[1])
        current = now or datetime.now().astimezone()
        if current.tzinfo is not None:
            current = current.astimezone()
        clock = current.timetz().replace(tzinfo=None)
        if start == end:
            return True
        if start < end:
            return start <= clock < end
        return clock >= start or clock < end

    def should_deliver(self, event: NotificationEvent, now: datetime | None = None) -> bool:
        tier = self.priority(event, now)
        return tier not in ("Mute",) and (tier == "Now" or not self.is_quiet(now))

    @staticmethod
    def _dedupe_key(event: NotificationEvent, created_at: str) -> str:
        if event.dedupe_key and event.dedupe_key.strip():
            return event.dedupe_key.strip()[:240]
        canonical = "\x1f".join((
            event.source.strip().casefold(),
            event.event_type.strip().casefold(),
            event.entity.strip().casefold(),
            event.title.strip().casefold(),
            event.body.strip().casefold(),
            created_at[:10],
        ))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> StoredNotification:
        return StoredNotification(**dict(row))

    def ingest(self, event: NotificationEvent, now: datetime | None = None) -> StoredNotification:
        if event.sensitive:
            raise ValueError("Sensitive notifications require encrypted storage, which is not configured.")
        source = event.source.strip()
        event_type = event.event_type.strip()
        title = event.title.strip()
        if not source or not event_type or not title:
            raise ValueError("Notification source, event type, and title are required.")
        if len(source) > 100 or len(event_type) > 100 or len(title) > 500:
            raise ValueError("Notification source, event type, or title is too long.")
        if len(event.body) > 10000:
            raise ValueError("Notification body is too long.")
        if event.deadline:
            _parse_datetime(event.deadline)

        created_at = _parse_datetime(event.created_at or now or datetime.now().astimezone()).isoformat()
        dedupe_key = self._dedupe_key(event, created_at)
        normalized = NotificationEvent(
            source=source,
            event_type=event_type,
            title=title,
            body=event.body,
            urgency=event.urgency,
            entity=event.entity.strip(),
            deadline=event.deadline,
            sentiment=event.sentiment,
            dedupe_key=dedupe_key,
            created_at=created_at,
        )
        priority = self.priority(normalized, now)
        with self._connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO notifications
                (dedupe_key, source, event_type, title, body, urgency, entity,
                 deadline, sentiment, created_at, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dedupe_key, source, event_type, title, event.body,
                    event.urgency.strip().casefold(), event.entity.strip(),
                    event.deadline, event.sentiment.strip().casefold(),
                    created_at, priority,
                ),
            )
            row = connection.execute(
                "SELECT * FROM notifications WHERE dedupe_key = ?", (dedupe_key,)
            ).fetchone()
        return self._from_row(row)

    def list_events(
        self,
        status: str | None = "new",
        priority: str | None = None,
        limit: int = 100,
    ) -> list[StoredNotification]:
        clauses = []
        values: list[object] = []
        if status:
            clauses.append("status = ?")
            values.append(status)
        if priority:
            clauses.append("priority = ?")
            values.append(priority)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        bounded_limit = max(1, min(int(limit), 500))
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM notifications {where} ORDER BY created_at DESC LIMIT ?",
                (*values, bounded_limit),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def mark_done(self, notification_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE notifications SET status = 'done', snoozed_until = NULL WHERE id = ?",
                (int(notification_id),),
            )
        return cursor.rowcount > 0

    def snooze(self, notification_id: int, until: str | datetime) -> bool:
        snoozed_until = _parse_datetime(until)
        if snoozed_until <= datetime.now(timezone.utc):
            raise ValueError("Snooze time must be in the future.")
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE notifications SET status = 'snoozed', snoozed_until = ? WHERE id = ? AND status != 'done'",
                (snoozed_until.isoformat(), int(notification_id)),
            )
        return cursor.rowcount > 0

    def digest(
        self,
        since: datetime,
        now: datetime | None = None,
        include_muted: bool = False,
    ) -> list[StoredNotification]:
        since_iso = _parse_datetime(since).isoformat()
        now_iso = _parse_datetime(now or datetime.now().astimezone()).isoformat()
        muted_clause = "" if include_muted else "AND priority != 'Mute'"
        with self._connect() as connection:
            rows = connection.execute(
                f"""SELECT * FROM notifications
                WHERE created_at >= ? AND created_at <= ? AND status != 'done'
                {muted_clause}
                ORDER BY CASE priority
                    WHEN 'Now' THEN 0 WHEN 'Today' THEN 1
                    WHEN 'This Week' THEN 2 WHEN 'FYI' THEN 3 ELSE 4 END,
                    created_at DESC""",
                (since_iso, now_iso),
            ).fetchall()
        return [self._from_row(row) for row in rows]