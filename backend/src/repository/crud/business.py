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

    async def read_business_by_reference_id(self, reference_id: str) -> Business:
        stmt = sqlalchemy.select(Business).where(Business.reference_id == reference_id)
        business = (await self.async_session.execute(stmt)).scalar_one_or_none()
        if business is None:
            raise EntityDoesNotExist(f"No business found for reference_id `{reference_id}`!")
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
        # Join the drop-off poll rotation immediately - see
        # src.workers.tasks.dropoff_detection.
        business.next_dropoff_poll_at = sqlalchemy_functions.now()  # type: ignore[assignment]

        await self.async_session.commit()
        await self.async_session.refresh(instance=business)
        return business

    async def list_due_for_dropoff_poll(
        self, *, now: datetime.datetime, limit: int
    ) -> typing.Sequence[Business]:
        """
        The drop-off poller's "circular queue": ACTIVE businesses due for their
        turn, oldest-due first, batch-limited so one sweep never calls the
        Orders API for every business at once.
        """
        stmt = (
            sqlalchemy.select(Business)
            .where(
                Business.status == "ACTIVE",
                Business.razorpay_account_id.is_not(None),
                sqlalchemy.or_(
                    Business.next_dropoff_poll_at.is_(None),
                    Business.next_dropoff_poll_at <= now,
                ),
            )
            .order_by(sqlalchemy.func.coalesce(Business.next_dropoff_poll_at, Business.created_at).asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return (await self.async_session.execute(stmt)).scalars().all()

    async def mark_dropoff_polled(
        self, *, business_id: int, polled_at: datetime.datetime, next_poll_at: datetime.datetime
    ) -> None:
        """Push this business to the back of the rotation."""
        stmt = (
            sqlalchemy.update(Business)
            .where(Business.id == business_id)
            .values(last_dropoff_poll_at=polled_at, next_dropoff_poll_at=next_poll_at)
        )
        await self.async_session.execute(stmt)
        await self.async_session.commit()

    async def update_agent_settings(self, *, business_id: int, agent_settings: dict) -> Business:
        stmt = (
            sqlalchemy.update(Business)
            .where(Business.id == business_id)
            .values(agent_settings=agent_settings, updated_at=sqlalchemy_functions.now())
            .returning(Business)
        )
        row = (await self.async_session.execute(stmt)).scalar_one_or_none()
        await self.async_session.commit()
        if row is None:
            raise EntityDoesNotExist(f"Business with id `{business_id}` does not exist!")
        return row

    def get_decrypted_access_token(self, business: Business) -> str:
        if not business.encrypted_access_token:
            raise RazorpayOAuthError("Business has no stored access token.")
        return get_data_encryptor().decrypt(business.encrypted_access_token)

    def get_decrypted_refresh_token(self, business: Business) -> str:
        if not business.encrypted_refresh_token:
            raise RazorpayOAuthError("Business has no stored refresh token.")
        return get_data_encryptor().decrypt(business.encrypted_refresh_token)
