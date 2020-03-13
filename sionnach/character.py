"""
Handles high-level communication between the system and individual character connections
"""


class Character:
    def __init__(self, client):
        self.client = client

        self.authenticated = False
        self.name = None
