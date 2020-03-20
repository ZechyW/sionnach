"""
Authentication management
"""
import bcrypt
from sqlalchemy.orm.exc import NoResultFound

from sionnach import log
from sionnach.character import Character
from sionnach.db import Help, User
from sionnach.exceptions import AuthInvalidPassword
from sionnach.server import Client

logger = log.logger(__name__)


class Auth:
    def __init__(self, db_session, mark_authenticated):
        self.db_session = db_session
        self.mark_authenticated = mark_authenticated

    async def authenticate_client(self, client: Client):
        """
        When passed unauthenticated clients, asynchronously attempts to authenticate
        them and registers them against the main controller's callback
        :param client:
        :return:
        """
        # Hello, client!
        login_msg: Help = self.db_session.query(Help).filter(Help.name == "LOGIN").one()
        client.send(f"{login_msg.text}\r\n\r\nName:")

        try:
            profile = await self._login(client)
        except AuthInvalidPassword:
            await client.close()
            return

        # At this point, the client has logged in successfully.
        character = Character(client=client, name=profile.name)
        return self.mark_authenticated(character)

    async def _login(self, client):
        """
        Attempt a login, from name to password
        Does not send the login prompt, since it could be different between calls
        :param client:
        :return:
        """
        name = ""
        while name.strip() == "":
            name = await client.async_receive()

        profile = None
        try:
            # Try to grab an existing profile and authenticate
            profile = (
                self.db_session.query(User).filter(User.name == name.lower()).one()
            )
            client.send(f"Password:")
            client.set_password_mode(True)
            password = await client.async_receive()
            if not bcrypt.checkpw(password.encode(), profile.password):
                client.send(f"Invalid password.")
                raise AuthInvalidPassword

        except NoResultFound:
            # Use the newly created profile
            profile = await self._new_user(client, name)

        client.set_password_mode(False)
        return profile

    async def _new_user(self, client, name):
        """
        Register a new user
        :param client:
        :param name:
        :return:
        """
        client.send(f"User not found.  Create a new user named '{name}'? (y/n)")
        response = await client.async_receive()

        if not response.startswith("y"):
            client.send("Enter a new user name.")
            return await self._login(client)

        pw_confirmed = False
        password = ""
        password2 = ""
        while not pw_confirmed:
            while password.strip() == "":
                client.set_password_mode(True)
                client.send("Enter a password for this user.")
                password = await client.async_receive()

            while password2.strip() == "":
                client.send("Enter the password again.")
                password2 = await client.async_receive()

            if password == password2:
                pw_confirmed = True
            else:
                password = ""
                password2 = ""

        client.set_password_mode(False)

        # Persist
        new_user = User(
            name=name, password=bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        )
        self.db_session.add(new_user)
        self.db_session.commit()

        return new_user
