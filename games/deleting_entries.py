from __future__ import unicode_literals
__author__ = 'xene'

from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
import logging
import models
import utils

logger = logging.getLogger(__name__)


def collect_entries():
    sports = models.Sport.objects.all()
    countries = models.Country.objects.all()
    seasons = models.Season.objects.all()
    sources = models.Source.objects.all()
    bookmakers = models.Bookmaker.objects.all()
    competitions = models.Competition.objects.all()
    competition_seasons = models.CompetitionSeason.objects.all()
    competition_season_infos = models.CompetitionSeasonInfo.objects.all()
    teams = models.Team.objects.all()
    team_infos = models.TeamInfo.objects.all()
    events = models.Event.objects.all()
    event_infos = models.EventInfo.objects.all()
    results = models.Result.objects.all()
    market_types = models.MarketType.objects.all()
    winner_odds = models.WinnerOdd.objects.all()
    market_results = models.MarketResult.objects.all()
    winner_offers = models.WinnerOffer.objects.all()
    winner_offer_odds = models.WinnerOfferOdd.objects.all()

    over_under_odds = models.OverUnderOdd.objects.all()
    over_under_offers = models.OverUnderOffer.objects.all()
    over_under_offer_odds = models.OverUnderOfferOdd.objects.all()

    finScRes = models.FinalScoreResult.objects.all()

    total_bets = models.TotalBet.objects.all()
    bets = models.Bet.objects.all()
    bet_events = models.BetEvent.objects.all()
    selections = models.Selection.objects.all()

    context = {'sports': sports, 'countries': countries, 'seasons': seasons, 'sources': sources,
               'competitions': competitions, 'competition_seasons': competition_seasons, 'bookmakers': bookmakers,
               'competition_season_infos': competition_season_infos, 'teams': teams, 'team_infos': team_infos,
               'events': events, 'event_infos': event_infos, 'results': results, 'market_types': market_types,
               'winner_odds': winner_odds, 'market_results': market_results, 'winner_offers': winner_offers,
               'winner_offer_odds': winner_offer_odds, 'over_under_odds': over_under_odds, 'over_under_offers':over_under_offers,
               'over_under_offer_odds': over_under_offer_odds,
               'final_score_results': finScRes, 'total_bets': total_bets, 'bets': bets,
               'bet_events': bet_events, 'selections': selections}
    return context


def delete_competitions(request):
    models.Competition.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_team_infos(request):
    models.TeamInfo.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_teams(request):
    models.Team.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_bookmakers(request):
    models.Bookmaker.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_events(request):
    models.Event.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_event_infos(request):
    models.EventInfo.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_market_types(request):
    models.MarketType.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


# TODO whenever a result is deleted, I must check all related events, update their status to 'Open' edit MarketOffers
# of their MarketTypes and update their market_result field to 'Open'. Also bet_event.selection status to 'Open'
# (Similar process must be done for every aggregated field). Maybe I should replace the results.delete method?
def delete_results(request):
    models.Result.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_winner_offers(request):
    models.WinnerOffer.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_winner_odds(request):
    models.WinnerOdd.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_winner_offer_odds(request):
    models.WinnerOfferOdd.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_over_under_offers(request):
    models.OverUnderOffer.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_over_under_odds(request):
    models.OverUnderOdd.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_over_under_offer_odds(request):
    models.OverUnderOfferOdd.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_market_results(request):
    models.MarketResult.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_total_bets(request):
    models.TotalBet.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_bets(request):
    models.Bet.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_bet_events(request):
    models.BetEvent.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_selections(request):
    models.Selection.objects.all().delete()
    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def delete_all(request):
    models.Sport.objects.all().delete()
    models.Country.objects.all().delete()
    models.Season.objects.all().delete()
    models.Source.objects.all().delete()
    models.Bookmaker.objects.all().delete()
    models.Team.objects.all().delete()
    models.TeamInfo.objects.all().delete()
    models.Competition.objects.all().delete()
    models.CompetitionSeason.objects.all().delete()
    models.CompetitionSeasonInfo.objects.all().delete()
    models.Team.objects.all().delete()
    models.Event.objects.all().delete()
    models.EventInfo.objects.all().delete()
    models.Result.objects.all().delete()
    models.MarketType.objects.all().delete()
    models.WinnerOdd.objects.all().delete()
    models.MarketResult.objects.all().delete()
    models.WinnerOffer.objects.all().delete()
    models.WinnerOfferOdd.objects.all().delete()

    models.FinalScoreResult.objects.all().delete()

    models.Bet.objects.all().delete()
    models.BetEvent.objects.all().delete()
    models.Selection.objects.all().delete()

    context = collect_entries()
    return render(request, 'games/unpopulate.html', context)


def clear_session(request):
    if request.session:
        request.session.clear()
    return HttpResponseRedirect(reverse('home'))

