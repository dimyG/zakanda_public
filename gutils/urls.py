from django.conf.urls import url
import views
from games.views import popular_raw_bevs


urlpatterns = [
    url(r'^TipsOverview/$', popular_raw_bevs, name='popular_raw_bevs'),
    url(r'^ContactUs/$', views.contact_us, name='contact_us'),
    url(r'^MiscData/$', views.misc_data, name='misc_data'),
    url(r'^UpdateSession/$', views.update_session, name='update_session'),
    url(r'^Features/$', views.features, name='features_details')
]

