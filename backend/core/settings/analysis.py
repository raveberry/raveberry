"""This module analyses provides an analysis of gathered data."""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Tuple

from dateutil import tz
from django.conf import settings as conf
from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.db.models import QuerySet
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils import dateparse, timezone

from core.models import ArchivedPlaylist, PlaylistEntry, PlayLog, RequestLog
from core.musiq import song_utils
from core.settings.settings import control


def _parse_datetimes(request: WSGIRequest) -> Tuple[datetime, datetime]:
    if request.method == "GET":
        params = request.GET
    else:
        params = request.POST

    startdate = params.get("startdate")
    starttime = params.get("starttime")
    enddate = params.get("enddate")
    endtime = params.get("endtime")
    if not startdate or not starttime or not enddate or not endtime:
        raise ValueError("All fields are required")

    start = dateparse.parse_datetime(startdate + "T" + starttime)
    end = dateparse.parse_datetime(enddate + "T" + endtime)

    if start is None or end is None:
        raise ValueError("invalid start-/endtime given")
    if start >= end:
        raise ValueError("start has to be before end")

    start = timezone.make_aware(start)
    end = timezone.make_aware(end)

    return start, end


def _most_active_device(
    session_key: str, count: int, request_logs: QuerySet[RequestLog]
) -> str:
    most_active_device = f"{session_key} ({count})"
    for index in range(6):
        if index >= request_logs.count():
            break
        most_active_device += "\n"
        if index == 5:
            most_active_device += "..."
        else:
            most_active_device += request_logs[index].item_displayname()
    return most_active_device


def _request_activity(
    start: datetime, end: datetime, request_logs: QuerySet[RequestLog]
) -> str:
    binsize = 3600
    number_of_bins = math.ceil((end - start).total_seconds() / binsize)
    request_bins = [0 for _ in range(number_of_bins)]

    for request_log in request_logs:
        seconds = (request_log.created - start).total_seconds()
        index = int(seconds / binsize)
        request_bins[index] += 1

    request_activity = ""
    current_time = start
    current_index = 0
    while current_time < end:
        request_activity += current_time.strftime("%H:%M")
        request_activity += ":\t" + str(request_bins[current_index])
        request_activity += "\n"
        current_time += timedelta(seconds=binsize)
        current_index += 1

    return request_activity


@control
def analyse(request: WSGIRequest) -> HttpResponse:
    """Perform an analysis of the database in the given timeframe."""

    try:
        start, end = _parse_datetimes(request)
    except ValueError as error:
        return HttpResponseBadRequest(error.args[0])

    played = PlayLog.objects.all().filter(created__gte=start).filter(created__lt=end)
    if not played.exists():
        return HttpResponseBadRequest("No songs played in the given time span")

    request_logs = (
        RequestLog.objects.all().filter(created__gte=start).filter(created__lt=end)
    )
    played_count = (
        played.values("song__url", "song__artist", "song__title")
        .annotate(count=models.Count("song__url"))
        .values("song__url", "song__artist", "song__title", "count")
        .order_by("-count")
    )
    played_votes = (
        PlayLog.objects.all()
        .filter(created__gte=start)
        .filter(created__lt=end)
        .order_by("-votes")
    )
    devices = (
        request_logs.values("session_key")
        .annotate(count=models.Count("session_key"))
        .values("session_key", "count")
        .order_by("-count")
    )

    response = {
        "songsPlayed": len(played),
        "mostPlayedSong": (
            song_utils.displayname(
                played_count[0]["song__artist"], played_count[0]["song__title"]
            )
            + f" ({played_count[0]['count']})"
        ),
        "highestVotedSong": (
            played_votes[0].song_displayname() + f" ({played_votes[0].votes})"
        ),
    }
    response["mostActiveDevice"] = _most_active_device(
        devices[0]["session_key"],
        devices[0]["count"],
        request_logs.filter(session_key=devices[0]["session_key"]),
    )

    response["requestActivity"] = _request_activity(start, end, request_logs)

    localtz = tz.gettz(conf.TIME_ZONE)
    playlist = ""
    for play_log in played:
        localtime = play_log.created.astimezone(localtz)
        playlist += f"[{localtime.hour:02d}:{localtime.minute:02d}] {play_log.song_displayname()}\n"
    response["playlist"] = playlist

    return JsonResponse(response)


@control
def save_as_playlist(request: WSGIRequest) -> HttpResponse:
    """Save the songs in the given timeframe as a playlist with the given name."""

    try:
        start, end = _parse_datetimes(request)
    except ValueError as error:
        return HttpResponseBadRequest(error.args[0])

    name = request.POST.get("name")
    if not name:
        return HttpResponseBadRequest("Name required")

    played = PlayLog.objects.all().filter(created__gte=start).filter(created__lt=end)

    list_id = f"playlog {str(start).replace(' ','T')} {str(end).replace(' ', 'T')}"

    playlist, created = ArchivedPlaylist.objects.get_or_create(
        list_id=list_id, title=name, counter=0
    )
    if not created:
        return HttpResponseBadRequest("Playlist already exists")

    song_index = 0
    for log in played:
        if not log.song:
            continue
        external_url = log.song.url
        PlaylistEntry.objects.create(
            playlist=playlist, index=song_index, url=external_url
        )
        song_index += 1

    return HttpResponse()
