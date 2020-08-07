__author__ = 'xene'

from django.conf.urls import url
from xmlSoccerParser import views

urlpatterns = [
    url(r'^LeaguesStandings/(?P<xmlSoccer_league_id>\d+)/$', views.get_league_standings, name='get_league_standings'),
    url(r'^Leagues/$', views.dummy_view, name='xmlsoccer_get_all_leagues'),
    url(r'^Teams/$', views.dummy_view, name='get_all_teams_by_league_and_season'),
    url(r'^Events/$', views.dummy_view, name='get_fixtures_by_date_interval'),
    url(r'^OddsForOpenEvents/$', views.dummy_view, name='get_odds_for_events'),
    url(r'^Results/$', views.dummy_view, name='get_results'),
]