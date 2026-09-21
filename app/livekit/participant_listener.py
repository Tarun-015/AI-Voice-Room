import asyncio

from livekit import rtc
from livekit.agents import inference, stt


class ParticipantListener:
    """
    Listens to one human participant.

    Pipeline:

        LiveKit participant
            ↓
        microphone audio
            ↓
        streaming STT
            ↓
        final transcript
    """

    def __init__(
        self,
        participant: rtc.RemoteParticipant,
        on_transcript,
    ):
        self.participant = participant
        self.identity = participant.identity
        self.on_transcript = on_transcript

        self.stt = inference.STT(
            model="deepgram/nova-3",
            language="multi",
        )

        self.stream = None
        self.stt_task = None
        self.audio_task = None

        self.running = False

    async def start(self):
        if self.running:
            return

        self.running = True

        print(
            f"[LISTENER] Starting: {self.identity}"
        )

        self.stream = self.stt.stream()

        self.stt_task = asyncio.create_task(
            self._read_transcripts()
        )

        self.audio_task = asyncio.create_task(
            self._read_audio()
        )

        await self.audio_task

    async def _read_audio(self):

        try:
            audio_stream = rtc.AudioStream.from_participant(
                participant=self.participant,
                track_source=rtc.TrackSource.SOURCE_MICROPHONE,
                sample_rate=24000,
                num_channels=1,
            )

            print(
                f"[LISTENER] Audio stream active: "
                f"{self.identity}"
            )

            async for event in audio_stream:

                if not self.running:
                    break

                self.stream.push_frame(
                    event.frame
                )

        except asyncio.CancelledError:
            pass

        except Exception as e:
            print(
                f"[AUDIO ERROR] "
                f"{self.identity}: {e}"
            )

        finally:
            await audio_stream.aclose()

    async def _read_transcripts(self):

        try:

            async for event in self.stream:

                if event.type != stt.SpeechEventType.FINAL_TRANSCRIPT:
                    continue

                if not event.alternatives:
                    continue

                text = (
                    event.alternatives[0]
                    .text
                    .strip()
                )

                if not text:
                    continue

                print(
                    f"\n[TRANSCRIPT]"
                    f"\n  speaker={self.identity}"
                    f"\n  text={text}\n"
                )

                await self.on_transcript(
                    self.identity,
                    text,
                )

        except asyncio.CancelledError:
            pass

        except Exception as e:
            print(
                f"[STT ERROR] "
                f"{self.identity}: {e}"
            )

    async def stop(self):

        if not self.running:
            return

        print(
            f"[LISTENER] Stopping: "
            f"{self.identity}"
        )

        self.running = False

        if self.audio_task:
            self.audio_task.cancel()

        if self.stt_task:
            self.stt_task.cancel()

        if self.stream:
            await self.stream.aclose()

        await self.stt.aclose()