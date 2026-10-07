from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from core.notification_brain import NotificationBrain, NotificationEvent


def test_notification_priority_combines_source_rules_vips_and_deadlines(tmp_path):
    now = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)
    inbox = NotificationBrain(
        tmp_path / "notifications.sqlite3",
        source_rules={"Kivra": "high", "TikTok": "mute"},
        vip_entities={"Mom"},
    )

    assert inbox.priority(NotificationEvent("Kivra", "letter", "Tax letter"), now) == "Today"
    assert inbox.priority(NotificationEvent("TikTok", "comment", "New comment"), now) == "Mute"
    assert inbox.priority(NotificationEvent("Mail", "message", "Hi", entity="Mom"), now) == "Today"
    assert inbox.priority(NotificationEvent(
        "Mail", "invoice", "Due", deadline=(now + timedelta(hours=2)).isoformat(),
    ), now) == "Now"


def test_quiet_hours_cross_midnight_but_urgent_events_bypass(tmp_path):
    inbox = NotificationBrain(tmp_path / "notifications.sqlite3", quiet_hours=("22:00", "07:00"))
    quiet_now = datetime(2026, 10, 7, 23, tzinfo=timezone.utc)
    normal = NotificationEvent("Mail", "message", "Newsletter")
    urgent = NotificationEvent("1177", "care", "Appointment", urgency="critical")

    assert inbox.is_quiet(quiet_now)
    assert not inbox.should_deliver(normal, quiet_now)
    assert inbox.should_deliver(urgent, quiet_now)


def test_ingest_is_idempotent_and_persists_across_instances(tmp_path):
    path = tmp_path / "notifications.sqlite3"
    event = NotificationEvent(
        "Postnord", "delivery", "Package out for delivery", dedupe_key="parcel-123",
        created_at="2026-10-07T09:00:00+00:00",
    )
    first = NotificationBrain(path).ingest(event)
    duplicate = NotificationBrain(path).ingest(event)

    assert duplicate.id == first.id
    assert len(NotificationBrain(path).list_events()) == 1


def test_snooze_complete_and_digest_lifecycle(tmp_path):
    path = tmp_path / "notifications.sqlite3"
    now = datetime.now(timezone.utc)
    inbox = NotificationBrain(path)
    item = inbox.ingest(NotificationEvent(
        "Mail", "invoice", "Electricity bill", created_at=now.isoformat(),
    ))

    assert inbox.snooze(item.id, now + timedelta(hours=1))
    assert inbox.list_events() == []
    assert inbox.list_events(status="snoozed")[0].id == item.id
    assert inbox.digest(now - timedelta(minutes=1))[0].id == item.id
    assert inbox.mark_done(item.id)
    assert inbox.digest(now - timedelta(minutes=1)) == []


def test_sensitive_notifications_are_rejected_until_encrypted_storage_exists(tmp_path):
    inbox = NotificationBrain(tmp_path / "notifications.sqlite3")
    with pytest.raises(ValueError, match="encrypted storage"):
        inbox.ingest(NotificationEvent("Kivra", "letter", "Tax decision", sensitive=True))