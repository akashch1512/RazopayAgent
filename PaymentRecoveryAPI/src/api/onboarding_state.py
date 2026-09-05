"""
The signed `state` token that carries onboarding form fields across the Razorpay
OAuth redirect.

Nothing is written to the database until the OAuth grant actually completes, so
the form fields a business owner submitted in step 1 ride along inside this
self-contained JWT and are read back in the callback.
"""

import datetime

from jose import jwt as jose_jwt

from src.config.manager import settings
from src.models.schemas.business import BusinessOnboardRequest

# How long a business owner has to complete the Razorpay OAuth grant before
# their onboarding attempt has to be restarted.
ONBOARDING_STATE_TTL_SECONDS = 900


def encode_onboarding_state(onboard: BusinessOnboardRequest) -> str:
    payload = {
        "name": onboard.name,
        "reference_id": onboard.reference_id,
        "contact_email": onboard.contact_email,
        "exp": datetime.datetime.now(tz=datetime.UTC)
        + datetime.timedelta(seconds=ONBOARDING_STATE_TTL_SECONDS),
    }
    return jose_jwt.encode(payload, key=settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_onboarding_state(state: str) -> dict:
    return jose_jwt.decode(state, key=settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
