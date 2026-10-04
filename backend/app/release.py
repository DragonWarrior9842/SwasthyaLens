"""Release entry point: deployment environment only, never local dotenv files."""

from app.core.config import Settings
from app.factory import create_app

settings = Settings(_env_file=None)
if not settings.secure_cookies:
    raise RuntimeError("The release entry point requires staging or production configuration")
app = create_app(settings)
