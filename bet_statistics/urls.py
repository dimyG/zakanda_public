from __future__ import unicode_literals
from django.conf.urls import url
import views
# import user_accounts.views

urlpatterns = [
    # url(r'^Profile/(?P<user_pk>\d+)/(?P<relation>\w+)/$', user_accounts.views.UsersList.as_view(), name='users_relation_list'),
    url(r'^Profile/(?P<user_pk>\d+)/$', views.profile_stats_template, name='profile_stats_template'),
    url(r'^Profile/Data/(?P<user_pk>\d+)/$', views.profile_stats_data, name='profile_stats_data'),
    url(r'BetEvents/$', views.BetEventList.as_view(), name='bet_event_list'),
    url(r'BetEventsTable/(?P<user_id>\d+)/$', views.bet_events_table_template, name='bet_events_table_template'),
    url(r'BetEventsTable/Data/(?P<user_id>\d+)/$', views.bet_events_table_data, name='bet_events_table_data'),
    url(r'TotalBetList/(?P<user_id>\d+)/$', views.total_bets_list, name='total_bets_list'),
    url(r'BetEvent/(?P<pk>\d+)/$', views.BetEventDetailView.as_view(), name='bet_event_detail'),
    url(r'TotalBet/(?P<pk>\d+)/$', views.TotalBetDetailView.as_view(), name='total_bet_detail'),
    url(r'RawBetEvent/TotalBets/(?P<raw_bev_id>\d+)$', views.raw_bev_tbs, name='raw_bev_tbs'),
]
