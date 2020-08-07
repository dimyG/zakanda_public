from django.conf.urls import url
import views

urlpatterns = [
    # url(r'^Create/$', views.BetTagCreate.as_view(), name='bet_tag_create'),
    url(r'^Create/$', views.bet_group_create, name='bet_tag_create'),
    # url(r'^(?P<pk>\d+)/Delete/$', views.BetTagDelete.as_view(), name='bet_tag_delete'),
    # url(r'^Edit/(?P<pk>\d+)/$', views.BetTagEdit.as_view(), name='bet_tag_edit'),
    url(r'^Edit/(?P<pk>\d+)/$', views.bet_group_edit, name='bet_tag_edit'),
    url(r'^List/User/(?P<target_user_id>\d+)/$', views.BetTagsList.as_view(), name='bet_tags_list'),
    url(r'^Select/$', views.SelectBetDetails.as_view(), name='select_bet_details'),
    # url(r'^(?P<id>\d+)/$', views.BetTagDetail.as_view(), name='bet_tag_detail'),
    url(r'^MakeDefault/(?P<bet_group_id>\d+)/$', views.make_default_view, name='make_default'),

    url(r'^Deposits/Create/$', views.DepositCreate.as_view(), name='deposit_create'),
    url(r'^Deposits/User/(?P<target_user_id>\d+)/$', views.DepositList.as_view(), name='deposits_list'),
    url(r'^Withdrawals/Create/$', views.WithdrawalCreate.as_view(), name='withdrawal_create'),

    url(r'^Notifications/Edit/(?P<pk>\d+)/$', views.NotificationSubscriptionEdit.as_view(), name='notifications_edit'),
    url(r'^List/Services/(?P<bet_group_id>\d+)/$', views.ServiceList.as_view(), name='service_list'),

    url(r'Balance/$', views.total_balance, name='total_balance'),

    url(r'^PaymentRequest/(?P<service_id>\d+)/$', views.payment_request, name='payment_request'),
    url(r'^BuyerDashboard/$', views.buyer_dashboard, name='buyer_dashboard'),
    url(r'^SellerDashboard/$', views.seller_dashboard, name='seller_dashboard'),
]
