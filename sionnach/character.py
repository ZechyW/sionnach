"""
Handles high-level communication between the system and individual character
connections
"""
import asyncio
from asyncio import QueueEmpty


class Character:
    def __init__(self, client, name):
        self.client = client
        self.name = name

    def get_input(self):
        """
        Returns the next currently available line of input for the given
        character (non-blocking)
        :return:
        """
        try:
            return self.client.input_queue.get_nowait()
        except QueueEmpty:
            return None

    def send(self, msg):
        """
        Sends a string to the given character
        :param msg:
        :return:
        """
        return self.client.send(msg)

    async def async_close(self):
        """
        Gracefully logs the character out and closes its client connection
        :return:
        """
        # TODO: Save, any other cleanup
        return await self.client.close()
