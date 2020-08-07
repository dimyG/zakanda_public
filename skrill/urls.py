from django.conf.urls import url
from django.views.decorators.csrf import csrf_exempt
# from django.views.generic.base import TemplateView
import views


urlpatterns = [
    url('^status_report/$', csrf_exempt(views.StatusReportView.as_view()), name='status_report'),
    # url('^cancel/$', TemplateView.as_view(template_name='skrill/cancel.html'), name='cancel'),
    # url('^return/$', TemplateView.as_view(template_name='skrill/return.html'), name='return'),
    # url(r'^PaymentRequest/$', views.payment_request, name='payment_request'),
    url(r'^TransferRequest/$', views.transfer_request, name='transfer_request'),
]
