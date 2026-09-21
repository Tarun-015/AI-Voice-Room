import asyncio

from dotenv import load_dotenv
from livekit import rtc

from livekit.agents import (
    AgentServer,
    JobContext,
    cli,
)

from app.livekit.participant_listener import (
    ParticipantListener,
)


load_dotenv()

server = AgentServer()


listeners = {}


async def start_listener(
    participant: rtc.RemoteParticipant,
):

    identity = participant.identity

    # Never listen to our own AI agents.
    if identity in {
        "roxstar-dost",
        "roxstar-sathi",
    }:
        return

    if identity in listeners:
        return

    print(
        f"[ROOM] Human participant detected: "
        f"{identity}"
    )

    listener = ParticipantListener(
        participant
    )

    listeners[identity] = listener

    try:
        await listener.start()

    except Exception as e:
        print(
            f"[LISTENER ERROR] "
            f"{identity}: {e}"
        )

    finally:
        listeners.pop(identity, None)


async def stop_listener(
    participant: rtc.RemoteParticipant,
):

    identity = participant.identity

    listener = listeners.pop(
        identity,
        None,
    )

    if listener:
        await listener.stop()


@server.rtc_session(
    agent_name="roxstar-multi-listener"
)
async def entrypoint(ctx: JobContext):

    print(
        f"\n================================"
        f"\nROXSTAR MULTI-USER LISTENER"
        f"\nROOM: {ctx.room.name}"
        f"\n================================\n"
    )

    await ctx.connect(
        auto_subscribe=rtc.AutoSubscribe.AUDIO_ONLY
    )

    ctx.room.on(
        "participant_connected",
        lambda participant: asyncio.create_task(
            start_listener(participant)
        ),
    )

    ctx.room.on(
        "participant_disconnected",
        lambda participant: asyncio.create_task(
            stop_listener(participant)
        ),
    )

    # Handle people already in the room.
    for participant in (
        ctx.room.remote_participants.values()
    ):
        asyncio.create_task(
            start_listener(participant)
        )

    # Keep the worker alive.
    await asyncio.Event().wait()


if __name__ == "__main__":
    cli.run_app(server)