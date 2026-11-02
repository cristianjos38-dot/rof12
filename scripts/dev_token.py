"""Print a laboratory JWT; tenant and roles are deliberately not token claims."""
import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import jwt

from app.config import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("user_id", nargs="?", default="user_001")
    args = parser.parse_args()
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": args.user_id, "iss": JWT_ISSUER, "aud": JWT_AUDIENCE, "exp": now + dt.timedelta(minutes=15), "iat": now}
    print(jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM))

