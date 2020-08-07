from django.conf.urls import include, url
# from django.views.decorators.cache import cache_page
# from zakanda.settings import cache_time
import views
import games.views


urlpatterns = [
    # The LeftSidebar/SportsList/ needs to be in front of r'List/$ since the later catches the List in SportsList
    url(r'^LeftSidebar/SportsList/$', views.left_sidebar_sports_list, name='left_sidebar_sports_list'),
    url(r'^LeftSidebar/UserInfo/(?P<user_pk>\d+)/$', views.left_sidebar_user_info, name='left_sidebar_user_info'),

    url(r'^$', views.profile, name='profile'),
    url(r'^List/$', views.UsersList.as_view(), name='users_list'),
    url(r'^Details/(?P<pk>\d+)/$', views.UserDetailView.as_view(), name='user_detail'),
    url(r'^Profile/(?P<user_pk>\d+)/(?P<relation>\w+)/$', views.UsersList.as_view(), name='users_relation_list'),
    # url(r'^LeaderBoard/$', cache_page(cache_time/3)(views.UsersList.as_view()), name='leader_board'),
    url(r'^LeaderBoard/$', views.Leaderboard.as_view(), name='leader_board'),
    url(r'^(?P<user_id>\d+)/Edit/$', views.edit_profile, name='edit_profile'),
    url(r'^(?P<user_id>\d+)/SellerSettings/$', views.seller_settings, name='seller_settings'),
    url(r'^StatsMode/$', views.stats_mode, name='stats_mode'),
    url(r'^Tips/(?P<user_pk>\d+)/$', games.views.user_tips_view, name='user_tips')
]
