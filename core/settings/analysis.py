"""This module analyses provides an analysis of gathered data."""
from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Tuple

from dateutil import tz
from django.conf import settings as conf
from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.utils import dateparse
from django.utils import timezone

import core.musiq.song_utils as song_utils
from core.models import PlayLog, ArchivedPlaylist, PlaylistEntry
from core.models import RequestLog
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


@control
def analyse(request: WSGIRequest) -> HttpResponse:
    """Perform an analysis of the database in the given timeframe."""

    try:
        start, end = _parse_datetimes(request)
    except ValueError as e:
        return HttpResponseBadRequest(e.args[0])

    played = PlayLog.objects.all().filter(created__gte=start).filter(created__lt=end)
    if not played.exists():
        return HttpResponseBadRequest("No songs played in the given time span")

    requested = (
        RequestLog.objects.all().filter(created__gte=start).filter(created__lt=end)
    )
    played_count = (
        played.values("song__url", "song__artist", "song__title")
        .values(
            "song__url", "song__artist", "song__title", count=models.Count("song__url")
        )
        .order_by("-count")
    )
    played_votes = (
        PlayLog.objects.all()
        .filter(created__gte=start)
        .filter(created__lt=end)
        .order_by("-votes")
    )
    devices = (
        requested.values("session_key")
        .values("session_key", count=models.Count("session_key"))
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
        "mostActiveDevice": (devices[0]["session_key"] + f" ({devices[0]['count']})"),
    }
    requested_by_session = requested.filter(session_key=devices[0]["session_key"])
    for i in range(6):
        if i >= len(requested_by_session):
            break
        response["mostActiveDevice"] += "\n"
        if i == 5:
            response["mostActiveDevice"] += "..."
        else:
            response["mostActiveDevice"] += requested_by_session[i].item_displayname()

    binsize = 3600
    number_of_bins = math.ceil((end - start).total_seconds() / binsize)
    request_bins = [0 for _ in range(number_of_bins)]

    for request_log in requested:
        seconds = (request_log.created - start).total_seconds()
        index = int(seconds / binsize)
        request_bins[index] += 1

    current_time = start
    current_index = 0
    response["requestActivity"] = ""
    while current_time < end:
        response["requestActivity"] += current_time.strftime("%H:%M")
        response["requestActivity"] += ":\t" + str(request_bins[current_index])
        response["requestActivity"] += "\n"
        current_time += timedelta(seconds=binsize)
        current_index += 1

    localtz = tz.gettz(conf.TIME_ZONE)
    playlist = ""
    for play_log in played:
        localtime = play_log.created.astimezone(localtz)
        playlist += "[{:02d}:{:02d}] {}\n".format(
            localtime.hour, localtime.minute, play_log.song_displayname()
        )
    response["playlist"] = playlist

    return JsonResponse(response)


@control
def save_as_playlist(request: WSGIRequest) -> HttpResponse:
    """Save the songs in the given timeframe as a playlist with the given name."""

    try:
        start, end = _parse_datetimes(request)
    except ValueError as e:
        return HttpResponseBadRequest(e.args[0])

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
        external_url = log.song.url
        PlaylistEntry.objects.create(
            playlist=playlist, index=song_index, url=external_url
        )
        song_index += 1

    return HttpResponse()
