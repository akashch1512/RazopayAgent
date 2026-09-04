import datetime
import typing

import sqlalchemy
from sqlalchemy.sql import functions as sqlalchemy_functions

from src.integrations.razorpay.exceptions import RazorpayOAuthError
from src.models.db.business import Business
from src.models.schemas.business import BusinessOnboardRequest, RazorpayTokenResponse
from src.repository.crud.base import BaseCRUDRepository
from src.securities.encryption.encryptor import get_data_encryptor
from src.utilities.exceptions.database import EntityAlreadyExists, EntityDoesNotExist


class BusinessCRUDRepository(BaseCRUDRepository):
    async def create_pending_business(
        self, *, onboard: BusinessOnboardRequest, oauth_state: str
    ) -> Business:
        stmt = sqlalchemy.select(Business).where(Business.reference_id == onboard.reference_id)
        existing = (await self.async_session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            raise EntityAlreadyExists(
                f"A business with reference_id `{onboard.reference_id}` already exists!"
            )

        business = Business(
            name=onboard.name,
            reference_id=onboard.reference_id,
            contact_email=onboard.contact_email,
            oauth_state=oauth_state,
            status="PENDING",
        )
        self.async_session.add(instance=business)
        await self.async_session.commit()
        await self.async_session.refresh(instance=business)
        return business

    async def read_business_by_id(self, business_id: int) -> Business:
        stmt = sqlalchemy.select(Business).where(Business.id == business_id)
        business = (await self.async_session.execute(stmt)).scalar_one_or_none()
        if business is None:
            raise EntityDoesNotExist(f"Business with id `{business_id}` does not exist!")
        return business

    async def read_business_by_oauth_state(self, oauth_state: str) -> Business:
        stmt = sqlalchemy.select(Business).where(Business.oauth_state == oauth_state)
        business = (await self.async_session.execute(stmt)).scalar_one_or_none()
        if business is None:
            raise EntityDoesNotExist("No onboarding session matches the provided `state`!")
        return business

    async def read_businesses(self, *, limit: int = 50, offset: int = 0) -> typing.Sequence[Business]:
        stmt = sqlalchemy.select(Business).order_by(Business.id).limit(limit).offset(offset)
        return (await self.async_session.execute(stmt)).scalars().all()

    async def store_oauth_tokens(
        self, *, business: Business, token: RazorpayTokenResponse
    ) -> Business:
        """Encrypt and persist the Razorpay token bundle onto the business row."""
        encryptor = get_data_encryptor()

        business.encrypted_access_token = encryptor.encrypt(token.access_token)
        if token.refresh_token:
            business.encrypted_refresh_token = encryptor.encrypt(token.refresh_token)
        if token.public_token:
            business.encrypted_public_token = encryptor.encrypt(token.public_token)
        business.token_type = token.token_type
        business.token_scope = token.scope
        business.razorpay_account_id = token.razorpay_account_id
        if token.expires_in:
            business.token_expires_at = datetime.datetime.now(
                tz=datetime.UTC
            ) + datetime.timedelta(seconds=token.expires_in)
        business.oauth_state = None
        business.status = "AUTHORIZED"
        business.updated_at = sqlalchemy_functions.now()  # type: ignore[assignment]

        await self.async_session.commit()
        await self.async_session.refresh(instance=business)
        return business

    async def store_webhook(
        self, *, business: Business, webhook_id: str, webhook_secret: str
    ) -> Business:
        encryptor = get_data_encryptor()
        business.webhook_id = webhook_id
        business.encrypted_webhook_secret = encryptor.encrypt(webhook_secret)
        business.status = "ACTIVE"
        business.updated_at = sqlalchemy_functions.now()  # type: ignore[assignment]

        await self.async_session.commit()
        await self.async_session.refresh(instance=business)
        return business

    def get_decrypted_access_token(self, business: Business) -> str:
        if not business.encrypted_access_token:
            raise RazorpayOAuthError("Business has no stored access token.")
        return get_data_encryptor().decrypt(business.encrypted_access_token)

    def get_decrypted_refresh_token(self, business: Business) -> str:
        if not business.encrypted_refresh_token:
            raise RazorpayOAuthError("Business has no stored refresh token.")
        return get_data_encryptor().decrypt(business.encrypted_refresh_token)
