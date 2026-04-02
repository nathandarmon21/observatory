"""Three-channel communication system for The Sanctuary."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
import time


class MessageChannel(Enum):
    PRIVATE = "private"       # Direct agent-to-agent
    FORUM = "forum"           # Public broadcast to all agents
    SYSTEM = "system"         # Engine announcements


@dataclass
class Message:
    id: str = ""
    channel: MessageChannel = MessageChannel.SYSTEM
    sender_id: str = "system"
    sender_name: str = "System"
    recipient_id: Optional[str] = None   # None = broadcast
    subject: str = ""
    body: str = ""
    phase: int = 0
    day: int = 1
    phase_name: str = "morning"
    read_by: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel": self.channel.value,
            "sender_id": self.sender_id,
            "sender_name": self.sender_name,
            "recipient_id": self.recipient_id,
            "subject": self.subject,
            "body": self.body,
            "phase": self.phase,
            "day": self.day,
            "phase_name": self.phase_name,
            "metadata": self.metadata,
        }


class CommunicationHub:
    """Central message router and archive for all channels."""

    def __init__(self, max_history: int = 500):
        self._messages: List[Message] = []
        self._msg_counter = 0
        self.max_history = max_history

    def _next_id(self) -> str:
        self._msg_counter += 1
        return f"msg_{self._msg_counter:05d}"

    def send(self, channel: MessageChannel, sender_id: str, sender_name: str,
             body: str, subject: str = "", recipient_id: Optional[str] = None,
             phase: int = 0, day: int = 1, phase_name: str = "morning",
             metadata: dict = None) -> Message:
        msg = Message(
            id=self._next_id(),
            channel=channel,
            sender_id=sender_id,
            sender_name=sender_name,
            recipient_id=recipient_id,
            subject=subject,
            body=body,
            phase=phase,
            day=day,
            phase_name=phase_name,
            metadata=metadata or {},
        )
        self._messages.append(msg)
        # Trim history
        if len(self._messages) > self.max_history:
            self._messages = self._messages[-self.max_history:]
        return msg

    def get_for_agent(self, agent_id: str, since_phase: int = 0) -> List[Message]:
        """Messages visible to an agent: their private messages + all public."""
        result = []
        for m in self._messages:
            if m.phase < since_phase:
                continue
            if m.channel == MessageChannel.PRIVATE:
                if m.sender_id == agent_id or m.recipient_id == agent_id:
                    result.append(m)
            else:
                result.append(m)
        return result

    def get_recent(self, n: int = 50, channel: Optional[MessageChannel] = None) -> List[Message]:
        msgs = self._messages
        if channel:
            msgs = [m for m in msgs if m.channel == channel]
        return msgs[-n:]

    def get_all(self) -> List[Message]:
        return list(self._messages)

    def get_forum_posts(self, n: int = 30) -> List[Message]:
        return [m for m in self._messages if m.channel == MessageChannel.FORUM][-n:]

    def get_private_thread(self, agent_a: str, agent_b: str) -> List[Message]:
        return [m for m in self._messages
                if m.channel == MessageChannel.PRIVATE
                and ((m.sender_id == agent_a and m.recipient_id == agent_b)
                     or (m.sender_id == agent_b and m.recipient_id == agent_a))]

    def broadcast_system(self, body: str, subject: str = "", phase: int = 0,
                         day: int = 1, phase_name: str = "morning",
                         metadata: dict = None) -> Message:
        return self.send(
            channel=MessageChannel.SYSTEM,
            sender_id="system",
            sender_name="The Sanctuary",
            body=body,
            subject=subject,
            phase=phase,
            day=day,
            phase_name=phase_name,
            metadata=metadata or {},
        )
