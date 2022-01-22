"""This file contains all exceptions related to this module."""


class ScreenProgramStopped(Exception):
    """Raised whenever a running screen program stopped execution.
    Usually through external reasons like closing the window."""
