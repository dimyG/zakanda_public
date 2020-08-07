from django.conf.urls import url
import views

urlpatterns = [
    url(r'^Dashboard/$', views.dashboard, name='dashboard'),
]
