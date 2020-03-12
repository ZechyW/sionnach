class RestartInterrupt(Exception):
    """
    Server Restart
    """

    def __init__(self):
        self.value = "RestartInterrupt"

    def __str__(self):
        return repr(self.value)


class ShutdownInterrupt(Exception):
    """
    Server Shutdown
    """

    def __init__(self):
        self.value = "ShutdownInterrupt"

    def __str__(self):
        return repr(self.value)
