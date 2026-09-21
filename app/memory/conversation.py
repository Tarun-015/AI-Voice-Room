from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConversationTurn:
    speaker: str
    text: str
    timestamp: str


class SharedConversationMemory:
    """
    Session-level memory shared by the Roxstar bots.

    Stores who said what so that the system can preserve
    multi-user conversation context.
    """

    def __init__(self, max_turns: int = 50):
        self.max_turns = max_turns
        self.turns: list[ConversationTurn] = []

    def add_turn(self, speaker: str, text: str) -> None:
        text = text.strip()

        if not text:
            return

        turn = ConversationTurn(
            speaker=speaker,
            text=text,
            timestamp=datetime.now().isoformat(),
        )

        self.turns.append(turn)

        # Keep memory bounded.
        if len(self.turns) > self.max_turns:
            self.turns = self.turns[-self.max_turns:]

    def recent_turns(self, limit: int = 10) -> list[ConversationTurn]:
        return self.turns[-limit:]

    def formatted_context(self, limit: int = 10) -> str:
        recent = self.recent_turns(limit)

        if not recent:
            return "No previous conversation."

        lines = []

        for turn in recent:
            lines.append(
                f"{turn.speaker}: {turn.text}"
            )

        return "\n".join(lines)

    def clear(self) -> None:
        self.turns.clear()