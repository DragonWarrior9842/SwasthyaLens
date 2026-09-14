"""Runtime entry point: validate configuration when the server imports the app."""

from app.factory import create_app

app = create_app()
