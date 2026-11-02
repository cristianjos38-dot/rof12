"""Print a clearly non-production local token fixture."""
import secrets


if __name__ == "__main__":
    print("dev_" + secrets.token_urlsafe(18))

