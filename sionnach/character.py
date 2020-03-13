"""
Handles high-level communication between the system and individual character connections
"""
from asyncio import QueueEmpty


class Character:
    def __init__(self, client):
        self.client = client

        self.authenticated = False
        self.name = None

    def get_input(self):
        """
        Returns the next currently available line of input for the given character (non-blocking)
        :return:
        """
        try:
            return self.client.input_queue.get_nowait()
        except QueueEmpty:
            return None
