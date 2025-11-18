from os import environ

# Use "0" as the default for integer env vars to avoid ValueError when not set
API_ID = int(environ.get("API_ID", "0"))  # Replace with your api id
API_HASH = environ.get("API_HASH", "")  # Replace with your api hash
BOT_TOKEN = environ.get("BOT_TOKEN", "")  # Replace with your bot token
OWNER_ID = int(environ.get("OWNER_ID", "0"))  # Replace with your owner id
