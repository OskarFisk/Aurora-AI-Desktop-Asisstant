"""Assistant tool for reviewing and managing the local notification inbox."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.notification_brain import NotificationBrain


def notification_inbox(parameters: dict, **_context) -> str:
    action = str(parameters.get("action", "list")).strip().casefold()
    inbox = NotificationBrain()
    if action == "list":
        events = inbox.list_events(limit=20)
        if not events:
            return "Your notification inbox is clear."
        return "\n".join(
            f"[{event.priority}] {event.source}: {event.title} (ID {event.id})"
            for event in events
        )
    if action == "done":
        if not inbox.mark_done(int(parameters["notification_id"])):
            return "That notification was not found."
        return "Notification marked done."
    if action == "snooze":
        notification_id = int(parameters["notification_id"])
        minutes = max(1, min(int(parameters.get("minutes", 60)), 10080))
        until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        if not inbox.snooze(notification_id, until):
            return "That notification was not found or is already done."
        return f"Notification snoozed for {minutes} minutes."
    if action == "digest":
        events = inbox.digest(datetime.now(timezone.utc) - timedelta(hours=24), include_muted=False)
        if not events:
            return "No notifications arrived in the last 24 hours."
        return "\n".join(
            f"[{event.priority}] {event.source}: {event.title}"
            for event in events[:50]
        )
    return "Choose list, digest, done, or snooze."


TOOL = {
    "name": "notification_inbox",
    "description": (
        "Review the local notification inbox, get its last-24-hour digest, "
        "mark an item done, or snooze it. Never invent notifications."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "enum": ["list", "digest", "done", "snooze"],
                "description": "Inbox operation to perform.",
            },
            "notification_id": {
                "type": "INTEGER",
                "description": "ID of the notification to complete or snooze.",
            },
            "minutes": {
                "type": "INTEGER",
                "description": "Snooze duration in minutes, from 1 to 10080.",
            },
        },
        "required": ["action"],
    },
    "handler": notification_inbox,
}