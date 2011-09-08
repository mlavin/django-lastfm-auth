from django.conf.urls.defaults import *


handler404 = 'lastfm_auth.tests.views.test_404'
handler500 = 'lastfm_auth.tests.views.test_500'


urlpatterns = patterns('',
    (r'^social-auth/', include('social_auth.urls')),
    (r'^default/', 'lastfm_auth.tests.views.default'),
    (r'^new/', 'lastfm_auth.tests.views.new'),
    (r'^error/', 'lastfm_auth.tests.views.error'),
)
