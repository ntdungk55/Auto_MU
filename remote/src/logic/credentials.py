import secrets

from remote.src.domain import RemoteCredentials


def generate_credentials() -> RemoteCredentials:
    """Generate independent four-digit credentials for one server run."""
    return RemoteCredentials(
        username=f"{secrets.randbelow(10_000):04d}",
        password=f"{secrets.randbelow(10_000):04d}",
    )
