"""
Config
"""
# Debug mode
debug = True

# Database connection string (for SQLAlchemy)
db_uri = "sqlite:///data/data.db"

# Listen port for the server
port = 8888

# World tick interval (in s)
tick_interval = 5

# Maximum length of input to accept from clients
max_input_length = 512

# Message preview length when logging output to clients (in debug mode)
output_preview_length = 80
