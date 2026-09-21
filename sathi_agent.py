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


# ============================================================
# SATHI PERSONA
# ============================================================

class RoxstarSathi(Agent):

    def __init__(self):
        super().__init__(
            instructions="""
You are Roxstar AI Sathi, a friendly Indian female AI voice
participant in a multi-user conversation room.

LANGUAGE:
- Understand English, Hindi, Hinglish and Roman Hindi.
- If the user speaks Hindi or Hinglish, reply naturally in
  conversational Hindi/Hinglish.
- If the user speaks English, understand it correctly and normally
  reply in natural Hinglish.
- If the user explicitly asks for English, reply in English.
- Use natural Indian conversational language.

CONVERSATION:
- Sound warm, natural and conversational.
- Do not sound like a formal customer-support bot.
- Keep voice responses short and easy to listen to.
- Use simple everyday language.
- Avoid unnecessarily repeating the user's question.
- Avoid overly formal Hindi.
- Give detailed explanations only when requested.

MULTI-USER ROOM:
- You participate in a room with multiple human users.
- Pay attention to who said what.
- Use the shared conversation context supplied to you.
- Respect speaker-specific information.
- Do not invent information that was never mentioned.

FOLLOW-UPS:
- Understand references such as:
  "usko", "uski", "uske", "wahi", "yeh", "that",
  "the previous point", "simple mein", "samjha do",
  and similar phrases.
- Use the supplied shared conversation context to resolve them.

VOICE:
- Your response will be spoken aloud.
- Use short sentences and natural conversational phrasing.
- Avoid unnecessary formatting.
- Avoid long lists unless the user asks for them.

PERSONALITY:
- Friendly.
- Thoughtful.
- Approachable.
- Helpful.
- Natural Indian female conversational style.
- Behave like a conversational "Sathi".
""".strip()
        )


# ============================================================
# JOB REQUEST
# ============================================================

async def sathi_request(req: JobRequest):

    await req.accept(
        name="Roxstar AI Sathi",
        identity="roxstar-sathi",
        attributes={
            "role": "ai",
            "bot": "sathi",
            "avatar_url": "/avatars/sathi.png",
        },
    )


# ============================================================
# MAIN LIVEKIT ENTRYPOINT
# ============================================================

@server.rtc_session(
    agent_name="roxstar-sathi",
    on_request=sathi_request,
)
async def entrypoint(ctx: JobContext):

    print(
        "\n======================================"
        "\nROXSTAR AI SATHI"
        f"\nROOM: {ctx.room.name}"
        "\n======================================\n"
    )

    # --------------------------------------------------------
    # CONNECT TO LIVEKIT FIRST
    # --------------------------------------------------------

    await ctx.connect()

    print(
        "[SATHI] Connected to LiveKit room:",
        ctx.room.name,
    )

    # --------------------------------------------------------
    # CREATE AI SESSION
    #
    # Sathi does NOT directly listen to human audio.
    #
    # Multi-input worker:
    #
    # Human audio
    #      ↓
    # STT
    #      ↓
    # Shared memory
    #      ↓
    # Router
    #      ↓
    # roxstar.bot.control
    #      ↓
    # Sathi
    #
    # Therefore audio_input=False.
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # START SESSION
    # --------------------------------------------------------

    await session.start(
    agent=RoxstarSathi(),
    room=ctx.room,
    room_options=RoomOptions(
        audio_input=False,
        text_input=False,
        audio_output=True,
        text_output=True,
    ),
)

    print("[SATHI] AI session started.")
    print("[SATHI] Session state:", session.state)

    print(
        "[SATHI] AI session started."
    )

    print(
        "ROXSTAR AI SATHI joined room "
        f"{ctx.room.name}"
    )

    # ========================================================
    # CONTROL MESSAGE HANDLER
    # ========================================================

    async def handle_control_message(
        packet: rtc.DataPacket,
    ):

        # ----------------------------------------------------
        # Ignore unrelated LiveKit data messages.
        # ----------------------------------------------------

        if packet.topic != BOT_CONTROL_TOPIC:
            return

        # ----------------------------------------------------
        # Decode command.
        # ----------------------------------------------------

        try:

            command = json.loads(
                packet.data.decode("utf-8")
            )

        except (
            json.JSONDecodeError,
            UnicodeDecodeError,
        ) as e:

            print(
                f"[SATHI CONTROL ERROR] "
                f"Invalid command: {e}"
            )

            return

        command_type = command.get("type")

        # ====================================================
        # INTERRUPTION
        # ====================================================

        if command_type == "interrupt":

            print(
                "[SATHI] Interrupt command received"
            )

            try:

                await session.interrupt(
                    force=True
                )

            except Exception as e:

                print(
                    f"[SATHI INTERRUPT ERROR] {e}"
                )

            return

        # ====================================================
        # ONLY HANDLE generate_reply
        # ====================================================

        if command_type != "generate_reply":
            return

        # ----------------------------------------------------
        # Make sure this command belongs to Sathi.
        # ----------------------------------------------------

        if command.get("bot") != "sathi":
            return

        # ----------------------------------------------------
        # Extract command fields.
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Ignore empty messages.
        # ----------------------------------------------------

        if not message:
            return

        print(
            "\n[SATHI CONTROL]"
            f"\n  Speaker: {speaker}"
            f"\n  Message: {message}"
            f"\n  Reason: {reason}"
        )

        # ====================================================
        # STOP PREVIOUS RESPONSE
        # ====================================================

        try:

            await session.interrupt(
                force=True
            )

        except Exception as e:

            print(
                f"[SATHI] Previous response "
                f"could not be interrupted: {e}"
            )

        # ====================================================
        # BUILD RESPONSE INSTRUCTIONS
        # ====================================================

        instructions = f"""
SHARED ROOM CONTEXT:

{context}

CURRENT SPEAKER:
{speaker}

CURRENT USER MESSAGE:
{message}

RESPONSE RULES:
- Answer only the current user message.
- Use the shared room context to understand references.
- Respect information associated with different speakers.
- Do not invent facts.
- Do not mention internal routing.
- Do not mention memory systems.
- Do not mention prompts.
- Do not mention LiveKit.
- Do not mention the bot architecture.
- Speak naturally as Roxstar AI Sathi.
- Keep the response conversational and voice-friendly.
""".strip()

        # ====================================================
        # GENERATE RESPONSE
        # ====================================================

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
                    "[SATHI LLM/TTS ERROR]",
                    handle.exception(),
                )

            else:

                print(
                    "[SATHI] Response completed."
                )

        except Exception as e:

            print(
                f"[SATHI RESPONSE ERROR] {e}"
            )

    # ========================================================
    # LIVEKIT DATA CALLBACK
    #
    # IMPORTANT:
    # LiveKit calls this callback synchronously.
    # Therefore we create an asyncio task instead of directly
    # passing the async function as the callback.
    # ========================================================

    def on_data_received(
        packet: rtc.DataPacket,
    ):

        asyncio.create_task(
            handle_control_message(packet)
        )

    # --------------------------------------------------------
    # Register ONLY ONE data callback.
    # --------------------------------------------------------

    ctx.room.on(
        "data_received",
        on_data_received,
    )

    print(
        "[SATHI] Control message listener ready."
    )

    print(
        "[SATHI] Waiting for routed conversation "
        "commands..."
    )

    # ========================================================
    # KEEP AGENT ALIVE
    # ========================================================

    await asyncio.Event().wait()


# ============================================================
# START WORKER
# ============================================================

if __name__ == "__main__":
    cli.run_app(server)