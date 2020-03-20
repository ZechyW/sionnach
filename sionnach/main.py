"""
Initialises the main loop controller.
The TCP server/client will be managed by a separate set of coroutines running
on the same event loop.
"""
import asyncio
from contextlib import suppress

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sionnach import exceptions, log, config
from sionnach.server import Server
from sionnach.auth import Auth
from sionnach.engine import Engine

logger = log.logger("sionnach.main")


class Act:
    def __init__(self):
        logger.info("== Sionnach ==")

        # SQLAlchemy ORM session
        self.db_session = None

        # Handles the low-level client/server interface
        self.server = None

        # Handles client authentication
        self.auth = None

        # Handles system logic
        self.engine = None

        # Holds client state for authentication
        self.unauthed_clients = []
        self.authed_chars = []

        # For calculating total uptime
        self.start_time = None

    async def run(self):
        """
        Initialises the server and runs the main loop until a shutdown is
        requested or an error occurs.
        :return:
        """
        logger.info("Initialising DB...")
        db_engine = create_engine(config.db_uri)
        session = sessionmaker(bind=db_engine)
        self.db_session = session()

        logger.info("Initialising server...")
        self.server = Server(
            register_client=self.register_client,
            deregister_client=self.deregister_client,
        )
        await self.server.start_server()

        logger.info("Initialising authentication...")
        self.auth = Auth(
            db_session=self.db_session, mark_authenticated=self.mark_authenticated
        )

        logger.info("Initialising engine...")
        self.engine = Engine(self.db_session)

        logger.info("Systems online.")

        self.start_time = asyncio.get_running_loop().time()

        try:
            await self.tick()
        except exceptions.RestartInterrupt:
            raise
        except exceptions.ShutdownInterrupt:
            raise

    async def tick(self):
        """
        Main loop.
        :return:
        """
        try:
            # Try to mitigate tick time drift
            tick_start = asyncio.get_running_loop().time()

            logger.debug(
                f"Main tick (up: "
                f"{asyncio.get_running_loop().time() - self.start_time}s)"
            )

            # World updates
            self.engine.tick()

            # Sleep through to next tick
            tick_time = asyncio.get_running_loop().time() - tick_start
            if tick_time < config.tick_interval:
                await asyncio.sleep(config.tick_interval - tick_time)
        except Exception:
            raise

        return await self.tick()

    def shutdown(self):
        """
        Cannot be run as an asynchronous task, or we get infinite recursion errors
        trying to get it to cancel itself
        :return:
        """
        logger.info("Shutting down.")
        loop = asyncio.get_event_loop()

        # Handle connections
        for client in self.unauthed_clients:
            loop.run_until_complete(client.close())

        for char in self.authed_chars:
            loop.run_until_complete(char.async_close())

        # Handle stray tasks
        pending = asyncio.all_tasks(loop)

        for task in pending:
            if not task.cancelled():
                task.cancel()

        with suppress(asyncio.CancelledError):
            loop.run_until_complete(asyncio.gather(*pending))

        loop.run_until_complete(loop.shutdown_asyncgens())

        logger.info("Shutdown complete.")

    # ----------------------------------
    # Character/client management
    # - Track new connections and logins
    # ----------------------------------
    def register_client(self, client):
        """
        Tracks new clients from the server
        :param client:
        :return:
        """
        self.unauthed_clients.append(client)
        logger.info(f"New connection from [{client.remote_ip}].")

        # Authentication is scheduled for asynchronous processing
        asyncio.create_task(self.auth.authenticate_client(client))

    def deregister_client(self, client):
        """
        Tracks clients that have dropped their connection to the server
        (intentionally or otherwise)
        :param client:
        :return:
        """
        # Just drop unauthenticated clients
        for unauthed in self.unauthed_clients:
            if unauthed == client:
                self.unauthed_clients.remove(client)
                return

        # For authenticated clients, we have to clear the character as well
        for authed in self.authed_chars:
            if authed.client == client:
                self.engine.remove_char(authed)
                self.authed_chars.remove(authed)

    def mark_authenticated(self, character):
        """
        Tracks characters that have passed through the authentication module
        :param character:
        :return:
        """
        self.unauthed_clients.remove(character.client)
        self.authed_chars.append(character)
        self.engine.add_char(character)


if __name__ == "__main__":
    actor = Act()

    # Handle high-level shutdown/restart interrupts
    try:
        asyncio.get_event_loop().run_until_complete(actor.run())
    except KeyboardInterrupt:
        logger.info("Shutdown requested via KeyboardInterrupt at console.")
        actor.shutdown()
