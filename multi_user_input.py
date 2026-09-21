import asyncio

from dotenv import load_dotenv
from livekit import rtc

from livekit.agents import (
    AgentServer,
    JobContext,
    JobRequest,
    cli,
)

from app.livekit.participant_listener import (
    ParticipantListener,
)

from app.memory.conversation_manager import (
    ConversationManager,
)

from app.routing.bot_control import (
    BOT_CONTROL_TOPIC,
    BotCommand,
)


load_dotenv()

server = AgentServer()

listeners = {}

conversation_manager = None
room = None


AI_IDENTITIES = {
    "roxstar-dost",
    "roxstar-sathi",
    "roxstar-input",
}


async def send_bot_command(result: dict):

    global room

    bot = result["bot"]

    command = BotCommand(
        bot=bot,
        speaker=result["speaker"],
        message=result["message"],
        context=result["context"],
        reason=result["reason"],
    )

    destination = f"roxstar-{bot}"

    print(
        "\n[ROUTER]"
        f"\n  Target: {bot}"
        f"\n  Destination: {destination}"
        f"\n  Reason: {result['reason']}"
    )

    try:

        await room.local_participant.publish_data(
            command.to_json(),
            reliable=True,
            destination_identities=[
                destination
            ],
            topic=BOT_CONTROL_TOPIC,
        )

        print(
            f"[ROUTER] Command sent to {bot}"
        )

    except Exception as e:

        print(
            f"[ROUTER ERROR] "
            f"Could not send command to "
            f"{bot}: {e}"
        )


async def handle_transcript(
    speaker: str,
    text: str,
):

    global conversation_manager

    print(
        "\n================================"
        "\n[CONVERSATION]"
        f"\nSpeaker : {speaker}"
        f"\nMessage : {text}"
        "\n================================"
    )

    try:

        result = (
            conversation_manager.process_turn(
                speaker=speaker,
                message=text,
            )
        )

        print(
            "\n[MEMORY]"
            f"\nSpeaker: {result['speaker']}"
            f"\nMessage: {result['message']}"
        )

        print(
            "\n[ROUTING]"
            f"\nBot: {result['bot']}"
            f"\nReason: {result['reason']}"
        )

        await send_bot_command(result)

    except Exception as e:

        print(
            f"[CONVERSATION ERROR] {e}"
        )


async def start_listener(
    participant: rtc.RemoteParticipant,
):

    identity = participant.identity

    # Never listen to AI participants.
    if identity in AI_IDENTITIES:
        return

    # Don't create duplicate listeners.
    if identity in listeners:
        return

    print(
        f"\n[ROOM] Human participant detected: "
        f"{identity}"
    )

    listener = ParticipantListener(
        participant=participant,
        on_transcript=handle_transcript,
    )

    listeners[identity] = listener

    try:

        await listener.start()

    except asyncio.CancelledError:

        pass

    except Exception as e:

        print(
            f"[LISTENER ERROR] "
            f"{identity}: {e}"
        )

    finally:

        listeners.pop(
            identity,
            None,
        )


async def stop_listener(
    participant: rtc.RemoteParticipant,
):

    identity = participant.identity

    listener = listeners.pop(
        identity,
        None,
    )

    if listener:

        print(
            f"[ROOM] Stopping listener: "
            f"{identity}"
        )

        await listener.stop()


async def input_request(
    req: JobRequest,
):

    await req.accept(
        name="Roxstar Multi User Input",
        identity="roxstar-input",
        attributes={
            "role": "system",
            "component": "multi-user-input",
        },
    )


@server.rtc_session(
    agent_name="roxstar-multi-input",
    on_request=input_request,
)
async def entrypoint(
    ctx: JobContext,
):

    global conversation_manager
    global room

    conversation_manager = (
        ConversationManager()
    )

    room = ctx.room

    print(
        "\n======================================"
        "\n ROXSTAR MULTI-USER INPUT"
        f"\n ROOM: {room.name}"
        "\n======================================\n"
    )

    # Subscribe to audio from human participants.
    await ctx.connect()

    # --------------------------------------------------
    # New participant joins.
    # --------------------------------------------------

    def on_participant_connected(
        participant,
    ):

        asyncio.create_task(
            start_listener(participant)
        )

    room.on(
        "participant_connected",
        on_participant_connected,
    )

    # --------------------------------------------------
    # Participant leaves.
    # --------------------------------------------------

    def on_participant_disconnected(
        participant,
    ):

        asyncio.create_task(
            stop_listener(participant)
        )

    room.on(
        "participant_disconnected",
        on_participant_disconnected,
    )

    # --------------------------------------------------
    # Audio track is published.
    #
    # This handles the case where a human joins first
    # and publishes their microphone afterward.
    # --------------------------------------------------

    def on_track_published(
        publication,
        participant,
    ):

        if publication.kind != rtc.TrackKind.KIND_AUDIO:
            return

        asyncio.create_task(
            start_listener(participant)
        )

    room.on(
        "track_published",
        on_track_published,
    )

    # --------------------------------------------------
    # Audio track becomes available.
    # --------------------------------------------------

    def on_track_subscribed(
        track,
        publication,
        participant,
    ):

        if publication.kind != rtc.TrackKind.KIND_AUDIO:
            return

        asyncio.create_task(
            start_listener(participant)
        )

    room.on(
        "track_subscribed",
        on_track_subscribed,
    )

    # --------------------------------------------------
    # Handle humans already present.
    # --------------------------------------------------

    for participant in (
        room.remote_participants.values()
    ):

        if participant.identity in AI_IDENTITIES:
            continue

        asyncio.create_task(
            start_listener(participant)
        )

    print(
        "[ROOM] Multi-user input layer ready."
    )

    print(
        "[ROOM] Waiting for human speech..."
    )

    # Keep worker alive.
    await asyncio.Event().wait()


if __name__ == "__main__":
    cli.run_app(server)