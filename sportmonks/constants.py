# -*- coding: utf-8 -*-
from enum import Enum


calls_limit = 1500  # per endpoint
interval = 1  # in hours (1500 per hour)

response_codes = {
    200:	"The request was successfull and data is returned",
    400:	"It seems that some part of the request is malformed. The exact reason is returned in the response.",
    401:	"The request is not authenticated",
    403:	"Not authorized. Indicates you're attempting to access a feed which is not accesible from your plan.",
    429:	"Too Many Requests. In order to make the API as responsive as possible, you have an hourly request limit. "
            "What this limit is for your current subscription can be found in any successfull response."
            "Check the 'meta' section to find out your limit.",
    500:	"An internal error has occurred, and has been logged for further inspection. "
            "Please email support if you are receiving this error.",
}

fetched_status = Enum(
    'FetchedStatus', [
        'NS',  # Not Started    -
        'LIVE',  # Live     -
        'HT',  # Half-Time'
        'FT',  # Full-Time'   -
        'ET',  # Extra-Time'
        'PEN_LIVE',  # Penalty Shootout
        'AET',  # Finished after extra time   -
        'BREAK',  # Match finished, waiting for extra time to start
        'FT_PEN',  # Full-Time after penalties    -
        'CANCL',  # Cancelled     -
        'POSTP',  # PostPhoned    -
        'INT',  # Interrupted     -
        'ABAN',	 # Abandoned      -
        'SUSP',  # -
        'AWARDED',
        'DELAYED',
        'TBA',  # To be Announced  (Fixture will be updated with exact time later)
        'WO',  # Walkover (Awarding of a victory to a contestant because there are no other contestants)
        # there is no status deleted in sportmonks. I have added it so that I mark events with it. Remove it from here
        'Deleted',  # the match was deleted for whatever reason. It is no more a valid match.
    ]
)

in_play_event = Enum(
    'InPlayEvent', [
        'goal',  # Goal
        'penalty',  # Goal via Penalty
        'missed_penalty',  # Penalty has been missed (* only available for major leagues)
        'own-goal',	 # Own goal
        'yellowcard',  # Yellow card for player
        'yellowred',  # 2nd yellow card for player resulting in red card
        'redcard',  # Direct red card
        'substitution',	 # A player get's substituted
        'pen_shootout_goal',  # Penalty in penalty shootout has been scored
        'pen_shootout_miss',
    ]
)


weather = Enum(
    'Weather', [
        'clear-sky',
        'few-clouds',
        'scattered-clouds',
        'broken-clouds',
        'shower-rain',
        'rain',
        'thunderstorm',
        'snow',
        'mist',
    ]
)

# I created this from the response info
soccer_market = [
    '3Way Result',
    '3Way Result 1st Half',
    '3Way Result 2nd Half',
    'Over/Under',
    'Over/Under 1st Half',
    'Over/Under 2nd Half',
    'Double Chance',
    'Handicap',  # no draw handicap
    '3Way Handicap',
    'Team To Score First',
    'Team To Score Last',
    'Both Teams to Score',
    'HT/FT Double',  # ημίχρονο τελικό
    'Home/Away',  # no draw
]
