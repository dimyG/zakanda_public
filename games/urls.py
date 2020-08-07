from django.conf.urls import url
import views
import deleting_entries
import gutils.markets_creation


urlpatterns = [
    # The competition_name regex: The first 3 expressions are to match 1,2,3 or 4 words separated by empty spaces
    # The following 3 are specifically for "2. Bundesliga", "Norvegian 1. Divisjon" and "Australian A-league"
    # Maybe its better to find a general scheme TODO low

    # url(r'^(?P<competition_gnames>\w+|\w+\s\w+|\w+\s\w+\s\w+|\w+\s\w+\s\w+\s\w+|\w+\W\s\w+|\w+\s\w+\W\s\w+|\w+\s\w+\W\w+|\w+-\w+\s\w+\\\w+)/'
    #     r'(?P<competition_ids>\d+)/PlannedEvents/$', views.planned_competition_events, name='planned_competition_events'),

    # Have in mind that planned_competition_events and all_markets_for_event urls are manually used in games
    # middleware so if you update them update that also.
    url(r'^(?P<competition_gnames>.*?)/'
        r'(?P<competition_ids>\d+)/PlannedEvents/$', views.planned_competition_events, name='planned_competition_events'),

    url(r'^PlannedEvents/AllMarkets/(?P<event_id>\d+)/$', views.all_markets_for_event, name='all_markets_for_event'),

    # url(r'^(\w+|\w+\s\w+|\w+\s\w+\s\w+|\w+\s\w+\s\w+\s\w+|\w+\W\s\w+|\w+\s\w+\W\s\w+|\w+\s\w+\W\w+)/PlannedEvents/(?P<event_id>\d+)/$',
    #     views.all_markets_for_event, name='all_markets_for_event'),
    # url(r'^(\w+|\w+\s\w+|\w+\s\w+\s\w+|\w+\s\w+\s\w+\s\w+|\w+\W\s\w+|\w+\s\w+\W\s\w+|\w+\s\w+\W\w+)/PlannedEvents/',
        # include('games.additional_urls', namespace='planned_events')),

    url(r'^PickBets/$', views.pick_bets, name='pick_bets'),

    url(r'^DeleteCompetitions/$', deleting_entries.delete_competitions, name='delete_competitions'),
    url(r'^DeleteTeams/$', deleting_entries.delete_teams, name='delete_teams'),
    url(r'^DeleteTeamInfos/$', deleting_entries.delete_team_infos, name='delete_team_infos'),
    url(r'^DeleteEvents/$', deleting_entries.delete_events, name='delete_events'),
    url(r'^DeleteEventInfos/$', deleting_entries.delete_event_infos, name='delete_event_infos'),
    url(r'^DeleteWinnerOffers/$', deleting_entries.delete_winner_offers, name='delete_winner_offers'),
    url(r'^DeleteWinnerOdds/$', deleting_entries.delete_winner_odds, name='delete_winner_odds'),
    url(r'^DeleteWinnerOfferOdds/$', deleting_entries.delete_winner_offer_odds, name='delete_winner_offer_odds'),

    url(r'^DeleteOverUnder25Offers/$', deleting_entries.delete_over_under_offers, name='delete_over_under_offers'),
    url(r'^DeleteOverUnder25Odds/$', deleting_entries.delete_over_under_odds, name='delete_over_under_odds'),
    url(r'^DeleteOverUnder25OfferOdds/$', deleting_entries.delete_over_under_offer_odds, name='delete_over_under_offer_odds'),

    url(r'^DeleteWinnerResults/$', deleting_entries.delete_market_results, name='delete_market_results'),
    url(r'^DeleteMarketTypes/$', deleting_entries.delete_market_types, name='delete_market_types'),

    url(r'^DeleteTotalBets/$', deleting_entries.delete_total_bets, name='delete_total_bets'),
    url(r'^DeleteBets/$', deleting_entries.delete_bets, name='delete_bets'),
    url(r'^DeleteBetEvents/$', deleting_entries.delete_bet_events, name='delete_bet_events'),
    url(r'^DeleteSelections/$', deleting_entries.delete_selections, name='delete_selections'),

    url(r'^DeleteResults/$', deleting_entries.delete_results, name='delete_results'),

    url(r'^DeleteAll/$', deleting_entries.delete_all, name='delete_all'),
    url(r'^ClearSession/$', deleting_entries.clear_session, name='clear_session'),

    url(r'^SimpleTest/$', gutils.markets_creation.test_init_markets, name='simple_test'),
    # url(r'^Populate/$', views.create_initial_data, name='create_initial_data'),


]