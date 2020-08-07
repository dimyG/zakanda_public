"""my_bet URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf.urls import include, url, patterns
from django.contrib import admin
from django.core.urlresolvers import reverse
import games.views
import gutils.views
import bet_slip.views
from django.conf import settings
from django.conf.urls.static import static
from django.views.i18n import javascript_catalog
import avatar_extension.views
from django_comments_xtd_extension.api import views as xtd_views
from django_comments_extension import views as comments_views
import django_comments_extension.views
import sportmonks.views
from django.conf.urls.i18n import i18n_patterns

# from django.core.mail import send_mail
# from settings import EMAIL_HOST_USER
# import django
# django.setup()
#
# send_mail('Django mail', 'Here is the message.', from_email=EMAIL_HOST_USER, recipient_list=[test_mail_01], fail_silently=False)

urlpatterns = [
    # PlaceBet and GetBetSlip must be in front of the allauth accounts url. This is because in case of
    # .../accounts/confirm-email/PlaceBet we want the placeBet to be called and not the embedded in allauth
    # .../accounts/confirm-email/whatever/ The problem appears when you press the signup form that returns a
    # .../accounts/confirm-email/ url and then the js calls the serve_initial_bet_form that calls the
    # .../accounts/confirm-email/PlaceBet/ url
    url(r'.*GetBetSlip/$', bet_slip.views.get_bet_slip, name='get_bet_slip'),
    url(r'.*PlaceBet/$', bet_slip.views.place_bet, name='place_bet'),
    # TODO low have in mind that the add_to_bet_slip can be called only from the planned_events view, so it might be
    # better to add the following url in the games urls
    url(r'.*AddToBetSlip/$', bet_slip.views.add_to_bet_slip, name='add_to_bet_slip'),
    url(r'.*RemoveFromBetSlip/$', bet_slip.views.remove_from_bet_slip, name='remove_from_bet_slip'),

    url(r'.*AjaxUpdSessionBookmaker/$', games.views.update_bookmaker_name_in_session, name='update_bookmaker_name_in_session'),
    url(r'^$', gutils.views.index, name='home'),

    url(r'^Users/', include('user_accounts.urls', namespace='user_accounts')),

    # The following line is to remove the extra confirmation step in logout
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}),
    # url(r'^accounts/login/$', 'allauth_extension.views.login_custom', name='login_custom'),
    url(r'^accounts/signup/$', 'allauth_extension.views.signup_custom', name='signup_custom'),
    url(r'^accounts/', include('allauth.urls')),

    url(r'^Stats/', include('bet_statistics.urls', namespace='bet_statistics')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^Sports/Football/', include('games.urls', namespace='games')),
    url(r'^Get/', include('xmlSoccerParser.urls', namespace='xmlSoccerParser')),

    url(r'^Feeds/', include('feeds.urls', namespace='feeds')),
    url(r'^Gutils/', include('gutils.urls', namespace='gutils')),
    url(r'^BetGroup/', include('bet_tagging.urls', namespace='bet_tagging')),

    # odds api endpoint
    # url(r'^api/v1.0/odds/$', sportmonks.views.odds_source_call, name='odds_api_v10'),

    url(r'^Skrill/', include('skrill.urls', namespace='skrill')),
    url(r'^Wallet/', include('wallet.urls', namespace='wallet')),

    # url(r'^gUtils/', include('gutils.urls', namespace='gutils')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += patterns('',
        url(r'^__debug__/', include(debug_toolbar.urls)),
    )

urlpatterns += patterns('',
    url(r'^django-rq/', include('django_rq.urls')),
    url(r'^activity/', include('actstream.urls')),

    url(r'^avatar/delete/$', avatar_extension.views.delete, name='special_avatar_delete'),
    url(r'^avatar/change/$', avatar_extension.views.change, name='special_avatar_change'),
    url(r'^avatar/add/$', avatar_extension.views.add, name='special_avatar_add'),
    url(r'^avatar/', include('avatar.urls')),

    # url(r'^blog/comments/', include('fluent_comments.urls')),
    # url(r'^comments/', include('django_ajax_comments_xtd.urls')),
    # url(r'^comments/sent/$', comments_xtd_extension.views.sent, name='special_comments-xtd-sent'),

    url(r'^comments/api/(?P<content_type>\w+[-]{1}\w+)/(?P<object_pk>[0-9]+)/$',
        xtd_views.CommentListCustom.as_view(), name='comments-xtd-api-list'),
    url(r'^comments/delete/(\d+)/$', django_comments_extension.views.delete, name='comments-delete_custom'),
    url(r'^comments/', include('django_comments_xtd.urls')),

    # url(r'^jsi18n/$', javascript_catalog, name='javascript-catalog'),
)

urlpatterns += [url(r'^i18n/', include('django.conf.urls.i18n'))]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # serving user uploaded files during development