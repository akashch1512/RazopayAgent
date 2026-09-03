class CredentialVerifier:
    def is_username_available(self, username: str | None) -> bool:
        return not username

    def is_email_available(self, email: str | None) -> bool:
        return not email


def get_credential_verifier() -> CredentialVerifier:
    return CredentialVerifier()


credential_verifier: CredentialVerifier = get_credential_verifier()
