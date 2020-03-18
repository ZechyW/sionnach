"""
Handles main system logic
- Parses input from users
- Performs system updates
- Sends output to users
"""
from sionnach import log

logger = log.logger("sionnach.engine")


class Engine:
    def __init__(self, db_session):
        # Link to main system DB
        self.db_session = db_session

        self.characters = []

    def add_char(self, character):
        """
        Start tracking a new user in the world
        :return:
        """
        self.characters.append(character)

    def remove_char(self, character):
        """
        Stop tracking a user in the world
        :return:
        """
        self.characters.remove(character)

    def tick(self):
        """
        Process actions for each user.
        Perform system update.
        Send any extra input to user.
        :return:
        """
        pass
