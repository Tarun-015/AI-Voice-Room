from app.memory.conversation import SharedConversationMemory
from app.memory.context_builder import ContextBuilder
from app.routing.router import ResponseRouter


class ConversationManager:
    """
    Central coordinator for the shared room conversation.

    Responsibilities:
    - Store speaker-aware conversation history
    - Decide which bot should respond
    - Build context for the selected bot
    """

    def __init__(self):
        self.memory = SharedConversationMemory()
        self.router = ResponseRouter()
        self.context_builder = ContextBuilder(
            self.memory
        )

    def process_turn(
        self,
        speaker: str,
        message: str,
    ) -> dict:

        # 1. Save the current user turn.
        self.memory.add_turn(
            speaker=speaker,
            text=message,
        )

        # 2. Decide which bot responds.
        decision = self.router.route(
            speaker=speaker,
            text=message,
        )

        # 3. Build context for that bot.
        context = self.context_builder.build(
            speaker=speaker,
            message=message,
        )

        return {
            "speaker": speaker,
            "message": message,
            "bot": decision.bot,
            "reason": decision.reason,
            "context": context,
        }