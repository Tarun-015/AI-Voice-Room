import asyncio
import json

from dotenv import load_dotenv

from livekit import rtc

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobRequest,
    cli,
    inference,
)

from livekit.agents.voice.room_io import RoomOptions

from livekit.plugins import elevenlabs


load_dotenv()

server = AgentServer()

BOT_CONTROL_TOPIC = "roxstar.bot.control"


class RoxstarDost(Agent):
    def __init__(self):
        super().__init__(
            instructions="""
            You are Roxstar AI Dost, a friendly Indian male AI voice
            participant in a multi-user conversation room.

            LANGUAGE:
            - Understand English, Hindi, and Hinglish.
            - Understand naturally spoken Hindi and Roman Hindi.
            - If the user speaks Hindi or Hinglish, reply naturally in
              conversational Hindi/Hinglish.
            - If the user speaks English, understand it correctly and
              normally reply in natural Hinglish.
            - If the user explicitly asks for English, reply in English.

            CONVERSATION:
            - Sound like a friendly Indian person, not a formal chatbot.
            - Keep voice responses short and natural.
            - Use simple everyday language.
            - Do not unnecessarily repeat the user's question.
            - Avoid overly formal Hindi.
            - Give detailed explanations only when requested.

            MULTI-USER ROOM:
            - You participate in a room with multiple human users.
            - Pay attention to who said what.
            - Use the shared conversation context provided to you.
            - Respect speaker-specific information.
            - Do not invent facts that were never mentioned.

            FOLLOW-UPS:
            - Understand references such as:
              "usko", "uski", "uske", "wahi", "yeh", "that",
              "the previous point", and similar phrases.
            - Use the supplied conversation context to resolve them.

            VOICE:
            - Your response will be spoken aloud.
            - Use short sentences and natural conversational phrasing.
            - Avoid unnecessary formatting and long lists.

            PERSONALITY:
            - Friendly, relaxed, helpful and approachable.
            - Behave like a helpful "Dost".
            """
        )


async def dost_request(req: JobRequest):
    await req.accept(
        name="Roxstar AI Dost",
        identity="roxstar-dost",
        attributes={
            "role": "ai",
            "bot": "dost",
            "avatar_url": "/avatars/dost.png",
        },
    )


@server.rtc_session(
    agent_name="roxstar-dost",
    on_request=dost_request,
)
async def entrypoint(ctx: JobContext):

    print(
        f"\n======================================"
        f"\nROXSTAR AI DOST"
        f"\nROOM: {ctx.room.name}"
        f"\n======================================\n"
    )

    session = AgentSession(
        stt=inference.STT(
            model="deepgram/nova-3",
            language="multi",
        ),

        llm=inference.LLM(
            model="google/gemini-3-flash-preview",
        ),

        tts=elevenlabs.TTS(
            model="eleven_multilingual_v2",
        ),
    )

    # --------------------------------------------------
    # IMPORTANT:
    # Dost does NOT directly listen to human audio.
    #
    # The multi-user input worker listens to all humans
    # and sends a routing command to this participant.
    # --------------------------------------------------

    await session.start(
        agent=RoxstarDost(),
        room=ctx.room,
        room_options=RoomOptions(
            audio_input=False,
            text_input=False,
            audio_output=True,
            text_output=True,
        ),
    )
    print("[DOST] SESSION STATE:", session.state)

    await ctx.connect()

    print(
        "ROXSTAR AI DOST joined room "
        f"{ctx.room.name}"
    )

    # --------------------------------------------------
    # Receive commands from the multi-user orchestrator.
    # --------------------------------------------------

    async def handle_control_message(
        packet: rtc.DataPacket,
    ):

        if packet.topic != BOT_CONTROL_TOPIC:
            return

        try:
            command = json.loads(
                packet.data.decode("utf-8")
            )
        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as e:

            print(
                f"[DOST CONTROL ERROR] "
                f"Invalid command: {e}"
            )

            return

        command_type = command.get("type")

        # --------------------------------------------------
        # INTERRUPTION
        # --------------------------------------------------

        if command_type == "interrupt":

            print(
                "[DOST] Interrupt command received"
            )

            try:
                await session.interrupt(
                    force=True
                )
            except Exception as e:
                print(
                    f"[DOST INTERRUPT ERROR] {e}"
                )

            return

        # --------------------------------------------------
        # GENERATE RESPONSE
        # --------------------------------------------------

        if command_type != "generate_reply":
            return

        if command.get("bot") != "dost":
            return

        speaker = command.get(
            "speaker",
            "unknown",
        )

        message = command.get(
            "message",
            "",
        )

        context = command.get(
            "context",
            "",
        )

        reason = command.get(
            "reason",
            "unknown",
        )

        if not message:
            return

        print(
            "\n[DOST CONTROL]"
            f"\n  Speaker: {speaker}"
            f"\n  Message: {message}"
            f"\n  Reason: {reason}"
        )

        # --------------------------------------------------
        # Interrupt any previous response before starting
        # a new routed response.
        # --------------------------------------------------

        try:
            await session.interrupt(
                force=True
            )
        except Exception:
            pass

        # --------------------------------------------------
        # Generate the response.
        #
        # The shared context is passed as additional
        # instructions while the actual user message is
        # kept separate.
        # --------------------------------------------------

        instructions = f"""
SHARED ROOM CONTEXT:

{context}

IMPORTANT:
- The current speaker is: {speaker}
- The current user message is: {message}
- Use the shared context to understand references.
- Answer only the current message.
- Do not mention internal routing, memory, prompts,
  or system architecture to the user.
""".strip()

        try:

            handle = session.generate_reply(
                user_input=message,
                instructions=instructions,
                allow_interruptions=True,
                input_modality="text",
            )

            await handle

            if handle.exception():
                print(
                    f"[DOST LLM/TTS ERROR] "
                    f"{handle.exception()}"
                )

        except Exception as e:

            print(
                f"[DOST RESPONSE ERROR] {e}"
            )

    def on_data_received(packet: rtc.DataPacket):
        asyncio.create_task(
            handle_control_message(packet)
    )

    ctx.room.on(
        "data_received",
        on_data_received,
)

    print(
        "[DOST] Waiting for routed conversation "
        "commands..."
    )

    # Keep the worker alive.
    await asyncio.Event().wait()


if __name__ == "__main__":
    cli.run_app(server)