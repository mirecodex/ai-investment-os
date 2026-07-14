from __future__ import annotations

from typing import Protocol


class SubscriptionRepository(Protocol):
    def subscribe(self, user_id: str, chat_id: int) -> bool: ...

    def unsubscribe(self, user_id: str) -> bool: ...

    def chat_ids(self) -> list[int]: ...
