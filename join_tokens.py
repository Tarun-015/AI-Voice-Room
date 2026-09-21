from dotenv import load_dotenv
from livekit import api
import os

load_dotenv()

ROOM = "roxstar-test"

API_KEY = os.getenv("LIVEKIT_API_KEY")
API_SECRET = os.getenv("LIVEKIT_API_SECRET")

def create_token(identity):
    token = (
        api.AccessToken(API_KEY, API_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=ROOM,
            )
        )
    )

    return token.to_jwt()


print("Human 1 token:")
print(create_token("Tarun"))

print("\nHuman 2 token:")
print(create_token("Krish"))