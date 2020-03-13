"""
Initialises the main loop controller.
The TCP server/client will be managed by a separate set of coroutines running on the same event loop.
"""
import asyncio

from sionnach import exceptions, log, config
from sionnach.engine import Engine
from sionnach.server import Server

logger = log.logger("sionnach.main")


class Act:
    def __init__(self):
        logger.info("== Sionnach ==")

        self.server = None

        self.engine = Engine()

        self.unauthed_clients = []
        self.authed_chars = []

    async def run_controller(self):
        """
        Initialises the server and starts iterating over the main loop.
        :return:
        """
        logger.info("Initialising server...")
        self.server = Server(
            register_client=self.register_client,
            deregister_client=self.deregister_client,
        )

        logger.info("Systems online.")
        try:
            asyncio.create_task(self.iterate_controller())
        except (exceptions.RestartInterrupt, exceptions.ShutdownInterrupt):
            asyncio.get_event_loop().stop()
            raise

    async def iterate_controller(self):
        """
        Main loop.
        :return:
        """
        try:
            # Login logic

            # World updates
            self.engine.tick()
            await asyncio.sleep(config.tick_interval)
        except Exception:
            raise

        return asyncio.create_task(self.iterate_controller())

    async def shutdown(self):
        pass

    # ----------------------------------
    # Character/client management
    # - Track new connections and logins
    # ----------------------------------
    def register_client(self, client):
        self.unauthed_clients.append(client)
        logger.info(f"New connection from [{client.remote_ip}].")

    def deregister_client(self, client):
        # Just drop unauthenticated clients
        for unauthed in self.unauthed_clients:
            if unauthed == client:
                self.unauthed_clients.remove(client)
                return

        # For authenticated clients, we have to clear the character as well
        for authed in self.authed_chars:
            if authed.client == client:
                self.engine.remove_char(authed)


def init():
    """
    Initialises the controller and runs the main system loop until a shutdown
    is requested.
    """
    actor = Act()
    loop = asyncio.get_event_loop()
    main_loop = loop.create_task(actor.run_controller())
    loop.run_forever()
    # === No processing occurs past this point until the loop stops ===

    # If the loop stopped, it's probably because someone requested a shutdown
    # or restart.  Clean up the controller and let the main script know what
    # happened.
    loop_exception = main_loop.exception()
    if loop_exception is not None:
        loop.run_until_complete(actor.shutdown())
        loop.close()
        raise loop_exception


if __name__ == "__main__":
    init()
