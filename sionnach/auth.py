"""
Authentication management
"""
from sqlalchemy.orm.exc import NoResultFound

from sionnach import log
from sionnach.character import Character
from sionnach.db import Help, User

logger = log.logger(__name__)


class Auth:
    def __init__(self, db_session, mark_authenticated):
        self.db_session = db_session
        self.mark_authenticated = mark_authenticated

    async def authenticate_client(self, client):
        """
        When passed unauthenticated clients and awaited, returns authenticated clients.
        :param client:
        :return:
        """
        # Hello, client!
        login_msg: Help = self.db_session.query(Help).filter(Help.name == "LOGIN").one()
        client.send(f"{login_msg.text}\r\n\r\nName:")

        # Name stage
        name = await client.async_receive()
        try:
            profile = (
                self.db_session.query(User).filter(User.name == name.lower()).one()
            )
        except NoResultFound:
            await self._new_user(client, name)

        # Register
        character = Character(client=client, name=name)

    async def _new_user(self, client, name):
        """
        Register a new user
        :param client:
        :param name:
        :return:
        """
        client.send(f"User not found.  Create a new user named '{name}'? (y/n)")
