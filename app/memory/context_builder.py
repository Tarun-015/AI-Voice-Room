from app.memory.conversation import SharedConversationMemory


class ContextBuilder:
    """
    Builds the context that is passed to the selected AI bot.

    Combines:
    - current speaker
    - current message
    - recent shared conversation
    """

    def __init__(
        self,
        memory: SharedConversationMemory,
    ):
        self.memory = memory

    def build(
        self,
        speaker: str,
        message: str,
        history_limit: int = 10,
    ) -> str:

        conversation = self.memory.formatted_context(
            limit=history_limit
        )

        return f"""
You are participating in a shared multi-user conversation.

CURRENT SPEAKER:
{speaker}

CURRENT MESSAGE:
{message}

RECENT SHARED CONVERSATION:
{conversation}

INSTRUCTIONS:
- Use the recent conversation to understand follow-ups.
- Pay attention to who said each statement.
- Resolve references such as "uski", "usko", "wahi",
  "that", and "the previous point" using conversation context.
- Do not invent information that is not present in the
  conversation.
- Answer the current speaker's actual question.
""".strip()