# AI Voice Room

A real-time multi-user AI voice room where two AI companions, **Roxstar AI Dost** and **Roxstar AI Sathi**, participate in conversations with human users.

The system is designed for natural Hindi/Hinglish conversations while understanding English input, maintaining shared conversational context, identifying speakers, and routing responses to the appropriate AI participant.

## Features

- Real-time voice communication using LiveKit
- Multiple human participants
- Two visible AI voice participants
  - AI Dost
  - AI Sathi
- Hindi/Hinglish conversational responses
- English input understanding
- Speaker-aware conversation context
- Shared conversation memory
- AI response routing
- Follow-up context understanding
- Voice interruption / barge-in handling
- Streaming speech-to-text and text-to-speech pipeline
- Logging for STT, routing, LLM and TTS stages
- Modular architecture for adding more AI participants

## Architecture

```text
Human Participants
       │
       ▼
   LiveKit Room
       │
       ▼
 Multi-user STT
       │
       ▼
 Speaker-aware Transcript
       │
       ▼
 Shared Conversation Memory
       │
       ▼
   Response Router
      /        \
     /          \
Dost            Sathi
  │               │
  ▼               ▼
Gemini           Gemini
  │               │
  ▼               ▼
ElevenLabs      ElevenLabs
  │               │
  └───────┬───────┘
          ▼
     LiveKit Room
