from django.core.urlresolvers import reverse


class PickBetsVaryMiddleware():
    """ it must be used if you want to modify the VARY header after the header has been modified by
    another django middleware. """
    def process_response(self, request, response):
        url = request.get_full_path().split("?")[0]
        urls = [
            reverse("games:pick_bets"),
            # in order to use this following url, all possible urls must be reversed (for all ids and gnames)
            # reverse("games:planned_competition_events", kwargs={"competition_ids": 720, "competition_gnames": "Name})
        ]
        if url in urls:
            response['VARY'] = ""
        elif url.find("PlannedEvents") and url.find("AllMarkets") == -1:
            response['VARY'] = ""
        return response