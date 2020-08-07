from django.conf.urls import url
import views

urlpatterns = [
    url(r'^Timeline/(?P<user_pk>\d+)/$', views.user_timeline, name='user_timeline'),
    url(r'^AggregatedTimeline/(?P<user_pk>\d+)/$', views.user_aggregated_timeline, name='user_aggregated_timeline'),
    url(r'^Notifications/(?P<user_id>\d+)/$', views.user_notification_timeline, name='user_notification_timeline'),
    url(r'^RawBetEvent/(?P<pk>\d+)/$', views.RawBetEventDetailView.as_view(), name='raw_bet_event_detail'),
    url(r'^StreamUserData/$', views.stream_user_data, name='stream_user_data'),
]
