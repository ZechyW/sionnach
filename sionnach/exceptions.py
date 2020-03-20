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


class AuthInvalidPassword(Exception):
    """
    Client failed to authenticate using given password
    """

    def __init__(self):
        self.value = "AuthInvalidPassword"

    def __str__(self):
        return repr(self.value)
