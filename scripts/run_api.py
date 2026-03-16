import uvicorn

from tgaggerator.api.app import app
from tgaggerator.config import settings


if __name__ == "__main__":
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
