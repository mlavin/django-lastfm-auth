from urlparse import urlparse, parse_qs

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase as DjangoTestCase
from django.utils import simplejson

import mock
from social_auth.models import UserSocialAuth
from social_auth import version as VERSION


if VERSION[1] == 3:
    DEFAULT_REDIRECT = getattr(settings, 'LOGIN_REDIRECT_URL', '')
    LOGIN_ERROR_URL = getattr(settings, 'LOGIN_ERROR_URL', settings.LOGIN_URL)
    NEW_USER_REDIRECT = DEFAULT_REDIRECT
    BEGIN_URL_NAME = 'begin'
    COMPLETE_URL_NAME = 'complete'
else:
    DEFAULT_REDIRECT = getattr(settings, 'SOCIAL_AUTH_LOGIN_REDIRECT_URL', '') or getattr(settings, 'LOGIN_REDIRECT_URL', '')
    LOGIN_ERROR_URL = getattr(settings, 'LOGIN_ERROR_URL', settings.LOGIN_URL)
    NEW_USER_REDIRECT = getattr(settings, 'SOCIAL_AUTH_NEW_USER_REDIRECT_URL', '')
    BEGIN_URL_NAME = 'socialauth_begin'
    COMPLETE_URL_NAME = 'socialauth_complete'


class AuthStartTestCase(DjangoTestCase):
    """Test login via Meetup."""

    def setUp(self):
        self.login_url = reverse(BEGIN_URL_NAME, kwargs={'backend': 'lastfm'})

    def test_redirect_url(self):
        """Check redirect to Last.fm."""
        response = self.client.get(self.login_url)
        # Don't use assertRedirect because we don't want to fetch the url
        self.assertTrue(response.status_code, 302)
        url = response['Location']
        scheme, netloc, path, params, query, fragment = urlparse(url)
        self.assertEqual('%s://%s%s' % (scheme, netloc, path), 'http://www.last.fm/api/auth/')
        query_data = parse_qs(query)
        self.assertEqual(query_data['api_key'][0], settings.LASTFM_API_KEY)
