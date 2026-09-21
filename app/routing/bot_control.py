from dataclasses import dataclass
import json


BOT_CONTROL_TOPIC = "roxstar.bot.control"


@dataclass
class BotCommand:
    bot: str
    speaker: str
    message: str
    context: str
    reason: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "type": "generate_reply",
                "bot": self.bot,
                "speaker": self.speaker,
                "message": self.message,
                "context": self.context,
                "reason": self.reason,
            }
        )

    @staticmethod
    def from_json(payload: str) -> "BotCommand":

        data = json.loads(payload)

        return BotCommand(
            bot=data["bot"],
            speaker=data["speaker"],
            message=data["message"],
            context=data["context"],
            reason=data["reason"],
        )