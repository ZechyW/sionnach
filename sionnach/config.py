"""
Config
"""
# Debug mode
debug = True

# Whether to enable the nested asyncio loop patch
nest_asyncio = True

# Database connection string (for SQLAlchemy)
db_uri = "sqlite:///data/data.db"

# Listen port for the server
port = 4000

# World tick interval (in s)
tick_interval = 5

# Maximum length of input to accept from clients
max_input_length = 512

# Message preview length when logging output to clients (in debug mode)
output_preview_length = 80
