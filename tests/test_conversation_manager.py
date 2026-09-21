from app.memory.conversation_manager import (
    ConversationManager,
)


manager = ConversationManager()


turns = [
    (
        "Tarun",
        "Maine Rahul ko A/B testing ka idea bataya.",
    ),
    (
        "Rahul",
        "Haan, mujhe woh interesting laga.",
    ),
    (
        "Tarun",
        "Usko simple mein samjhao.",
    ),
]


for speaker, message in turns:

    result = manager.process_turn(
        speaker=speaker,
        message=message,
    )

    print("\n" + "=" * 50)

    print(
        f"Speaker : {result['speaker']}"
    )

    print(
        f"Message : {result['message']}"
    )

    print(
        f"Bot     : {result['bot']}"
    )

    print(
        f"Reason  : {result['reason']}"
    )

    print("\nContext:")
    print(result["context"])