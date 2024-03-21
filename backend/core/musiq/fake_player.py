from core.musiq import player


class FakePlayer(player.Player):
    def start_song(self, song, catch_up: float):
        pass

    def play_alarm(self, interrupt: bool, alarm_path: str) -> None:
        pass

    def play_backup_stream(self):
        pass


def restart() -> None:
    pass


def seek_backward(_seek_distance: float) -> None:
    pass


def play() -> None:
    pass


def pause() -> None:
    pass


def seek_forward(_seek_distance: float) -> None:
    pass


def skip() -> None:
    pass


def set_volume(_volume) -> None:
    pass
