from dataclasses import dataclass
import re


@dataclass
class RoutingDecision:
    bot: str
    reason: str


class ResponseRouter:
    """
    Decides which Roxstar bot should respond.

    Routing priority:
    1. Explicitly addressed bot
    2. Contextual follow-up
    3. Alternating fallback

    Only one bot is selected for each user turn.
    """

    def __init__(self):
        self.last_bot = "sathi"

    def route(
        self,
        speaker: str,
        text: str,
    ) -> RoutingDecision:

        normalized = text.lower().strip()

        # --------------------------------------------------
        # 1. Explicitly addressed bot
        # --------------------------------------------------

        if self._mentions_dost(normalized):
            self.last_bot = "dost"

            return RoutingDecision(
                bot="dost",
                reason="explicit_address",
            )

        if self._mentions_sathi(normalized):
            self.last_bot = "sathi"

            return RoutingDecision(
                bot="sathi",
                reason="explicit_address",
            )

        # --------------------------------------------------
        # 2. Follow-up / conversational messages
        # --------------------------------------------------

        follow_up_patterns = [
            r"\busko\b",
            r"\buski\b",
            r"\buske\b",
            r"\bwahi\b",
            r"\byehi\b",
            r"\bthat\b",
            r"\bthis\b",
            r"\bsimple mein\b",
            r"\bsimply\b",
            r"\bexplain karo\b",
            r"\bsamjha\b",
        ]

        if any(
            re.search(pattern, normalized)
            for pattern in follow_up_patterns
        ):
            return RoutingDecision(
                bot=self.last_bot,
                reason="follow_up",
            )

        # --------------------------------------------------
        # 3. Normal question
        # --------------------------------------------------

        # Alternate between bots so that one bot does not
        # dominate the entire conversation.
        next_bot = (
            "dost"
            if self.last_bot == "sathi"
            else "sathi"
        )

        self.last_bot = next_bot

        return RoutingDecision(
            bot=next_bot,
            reason="balanced_fallback",
        )

    @staticmethod
    def _mentions_dost(text: str) -> bool:
        patterns = [
            r"\bdost\b",
            r"\broxstar dost\b",
        ]

        return any(
            re.search(pattern, text)
            for pattern in patterns
        )

    @staticmethod
    def _mentions_sathi(text: str) -> bool:
        patterns = [
            r"\bsathi\b",
            r"\broxstar sathi\b",
        ]

        return any(
            re.search(pattern, text)
            for pattern in patterns
        )