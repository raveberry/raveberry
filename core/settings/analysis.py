"""This module analyses provides an analysis of gathered data."""
from __future__ import annotations

import math
import subprocess
from datetime import timedelta
from typing import Dict, TYPE_CHECKING, Optional, List

from dateutil import tz
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import JsonResponse
from django.utils import dateparse
from django.utils import timezone

import core.musiq.song_utils as song_utils
from core.models import PlayLog
from core.models import RequestLog
from core.settings.settings import Settings

if TYPE_CHECKING:
    from core.base import Base


class Analysis:
    """This class is responsible for handling the analysis."""

    def __init__(self, base: "Base"):
        self.base = base

    @Settings.option
    def analyse(self, request: WSGIRequest) -> HttpResponse:
        """Perform an analysis of the database in the given timeframe."""
        startdate = request.POST.get("startdate")
        starttime = request.POST.get("starttime")
        enddate = request.POST.get("enddate")
        endtime = request.POST.get("endtime")
        if not startdate or not starttime or not enddate or not endtime:
            return HttpResponseBadRequest("All fields are required")

        start = dateparse.parse_datetime(startdate + "T" + starttime)
        end = dateparse.parse_datetime(enddate + "T" + endtime)

        if start is None or end is None:
            return HttpResponseBadRequest("invalid start-/endtime given")
        if start >= end:
            return HttpResponseBadRequest("start has to be before end")

        start = timezone.make_aware(start)
        end = timezone.make_aware(end)

        played = (
            PlayLog.objects.all().filter(created__gte=start).filter(created__lt=end)
        )
        requested = (
            RequestLog.objects.all().filter(created__gte=start).filter(created__lt=end)
        )
        played_count = (
            played.values("song__url", "song__artist", "song__title")
            .values(
                "song__url",
                "song__artist",
                "song__title",
                count=models.Count("song__url"),
            )
            .order_by("-count")
        )
        played_votes = (
            PlayLog.objects.all()
            .filter(created__gte=start)
            .filter(created__lt=end)
            .order_by("-votes")
        )
        devices = requested.values("address").values(
            "address", count=models.Count("address")
        )

        response = {
            "songs_played": len(played),
            "most_played_song": (
                song_utils.displayname(
                    played_count[0]["song__artist"], played_count[0]["song__title"]
                )
                + f" ({played_count[0]['count']})"
            ),
            "highest_voted_song": (
                played_votes[0].song_displayname() + f" ({played_votes[0].votes})"
            ),
            "most_active_device": (devices[0]["address"] + f" ({devices[0]['count']})"),
        }
        requested_by_ip = requested.filter(address=devices[0]["address"])
        for i in range(6):
            if i >= len(requested_by_ip):
                break
            response["most_active_device"] += "\n"
            if i == 5:
                response["most_active_device"] += "..."
            else:
                response["most_active_device"] += requested_by_ip[i].item_displayname()

        binsize = 3600
        number_of_bins = math.ceil((end - start).total_seconds() / binsize)
        request_bins = [0 for _ in range(number_of_bins)]

        for request_log in requested:
            seconds = (request_log.created - start).total_seconds()
            index = int(seconds / binsize)
            request_bins[index] += 1

        current_time = start
        current_index = 0
        response["request_activity"] = ""
        while current_time < end:
            response["request_activity"] += current_time.strftime("%H:%M")
            response["request_activity"] += ":\t" + str(request_bins[current_index])
            response["request_activity"] += "\n"
            current_time += timedelta(seconds=binsize)
            current_index += 1

        localtz = tz.gettz(settings.TIME_ZONE)
        playlist = ""
        for play_log in played:
            localtime = play_log.created.astimezone(localtz)
            playlist += "[{:02d}:{:02d}] {}\n".format(
                localtime.hour, localtime.minute, play_log.song_displayname()
            )
        response["playlist"] = playlist

        return JsonResponse(response)
