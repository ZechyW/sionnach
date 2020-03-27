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
from sionnach.util import get_helpfile

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
        client.send(get_helpfile(self.db_session, "LOGIN"))
        client.send_raw(f"Name: ")

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

        try:
            # Try to grab an existing profile and authenticate
            profile = (
                self.db_session.query(User).filter(User.name == name.lower()).one()
            )
            client.send_raw(f"Password: ")
            client.set_password_mode(True)
            password = await client.async_receive()
            # Add a newline here, because password mode stops the client-side newline
            # echo
            client.send("")
            if not bcrypt.checkpw(password.encode(), profile.password):
                client.send(f"Invalid password.")
                raise AuthInvalidPassword

        except NoResultFound:
            # Use the newly created profile
            profile = await self._new_user(client, name)

        # Authenticated.
        client.set_password_mode(False)
        client.send(get_helpfile(self.db_session, "MOTD"))
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
