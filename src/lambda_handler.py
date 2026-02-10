"""AWS Lambda handler for the API (API Gateway → Lambda → FastAPI via Mangum)."""

import os

os.environ.setdefault("AWS_LAMBDA", "1")

from mangum import Mangum
from src.main import app

handler = Mangum(app, lifespan="off")
