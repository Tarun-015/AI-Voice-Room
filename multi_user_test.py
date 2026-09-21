import asyncio
import logging

from dotenv import load_dotenv
from livekit import rtc

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    AutoSubscribe,
    JobContext,
    StopResponse,
    cli,
    inference,
    llm,
    room_io,
    utils,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("multi-user-test")


class ParticipantListener(Agent):

    def __init__(self, participant_identity: str):
        super().__init__(
            instructions="You are only a speech transcription listener.",
            stt=inference.STT(
                model="deepgram/nova-3",
                language="multi",
            ),
        )

        self.participant_identity = participant_identity

    async def on_user_turn_completed(
        self,
        chat_ctx: llm.ChatContext,
        new_message: llm.ChatMessage,
    ):
        text = new_message.text_content

        print(
            f"\n[TRANSCRIPT] "
            f"{self.participant_identity}: {text}\n"
        )

        # Do not generate an AI response.
        raise StopResponse()


class MultiUserListener:

    def __init__(self, ctx: JobContext):
        self.ctx = ctx

        self.sessions: dict[str, AgentSession] = {}
        self.tasks: set[asyncio.Task] = set()

    def start(self):

        self.ctx.room.on(
            "participant_connected",
            self.on_participant_connected,
        )

        self.ctx.room.on(
            "participant_disconnected",
            self.on_participant_disconnected,
        )

    def on_participant_connected(
        self,
        participant: rtc.RemoteParticipant,
    ):

        identity = participant.identity

        if identity in self.sessions:
            return

        print(f"\n[USER JOINED] {identity}")

        task = asyncio.create_task(
            self._start_session(participant)
        )

        self.tasks.add(task)

        def task_done(t):
            self.tasks.discard(t)

            try:
                session = t.result()
                self.sessions[identity] = session
            except Exception as e:
                logger.exception(
                    f"Failed to start session for {identity}: {e}"
                )

        task.add_done_callback(task_done)

    def on_participant_disconnected(
        self,
        participant: rtc.RemoteParticipant,
    ):

        identity = participant.identity

        print(f"\n[USER LEFT] {identity}")

        session = self.sessions.pop(identity, None)

        if session:
            task = asyncio.create_task(
                self._close_session(session)
            )

            self.tasks.add(task)
            task.add_done_callback(
                lambda _: self.tasks.discard(task)
            )

    async def _start_session(
        self,
        participant: rtc.RemoteParticipant,
    ):

        identity = participant.identity

        session = AgentSession()

        await session.start(
            agent=ParticipantListener(identity),
            room=self.ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=True,
                text_output=False,
                audio_output=False,
                participant_identity=identity,
                text_input=False,
            ),
        )

        print(
            f"[LISTENER READY] listening to {identity}"
        )

        return session

    async def _close_session(
        self,
        session: AgentSession,
    ):

        await session.drain()
        await session.aclose()

    async def aclose(self):

        await utils.aio.cancel_and_wait(
            *self.tasks
        )

        await asyncio.gather(
            *[
                self._close_session(session)
                for session in self.sessions.values()
            ],
            return_exceptions=True,
        )

        self.sessions.clear()


server = AgentServer()


@server.rtc_session(
    agent_name="roxstar-multi-test"
)
async def entrypoint(ctx: JobContext):

    print(
        f"\nROXSTAR MULTI-USER TEST"
        f"\nRoom: {ctx.room.name}\n"
    )

    listener = MultiUserListener(ctx)

    listener.start()

    await ctx.connect(
        auto_subscribe=AutoSubscribe.AUDIO_ONLY
    )

    # Handle participants already in the room.
    for participant in ctx.room.remote_participants.values():
        listener.on_participant_connected(participant)

    async def cleanup():
        await listener.aclose()

    ctx.add_shutdown_callback(cleanup)


if __name__ == "__main__":
    cli.run_app(server)