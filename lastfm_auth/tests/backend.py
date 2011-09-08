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


def lastfm_user_response():
    return {
        "name": "RJ",
        "realname": "Richard Jones",
        "image": [
            {"#text": "http://userserve-ak.last.fm/serve/34/8270359.jpg", "size":"small"},
            {"#text": "http:/userserve-ak.last.fm/serve/64/8270359.jpg", "size":"medium"},
            {"#text": "http:/userserve-ak.last.fm/serve/126/8270359.jpg", "size":"large"},
            {"#text": "http://userserve-ak.last.fm/serve/252/8270359.jpg", "size":"extralarge"}
        ],
        "url": "http://www.last.fm/user/RJ",
        "id": "1000002",
        "country": "UK",
        "age": 29,
        "gender": "m",
        "subscriber": 1,
        "playcount": 61798,
        "playlists": 4,
        "bootstrap": "0",
        "registered": {"#text":"2002-11-20 11:50", "unixtime":"1037793040"}
    }


class AuthStartTestCase(DjangoTestCase):
    """Test login via Lastfm."""

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


class ContribAuthTestCase(DjangoTestCase):
    """Validate contrib.auth calls."""
    
    def test_has_get_user(self):
        """Authentication backend must define a get_user method."""
        from lastfm_auth.backend import LastfmBackend
        get_user = getattr(LastfmBackend, 'get_user', None)
        self.assertTrue(get_user, "Auth backend must define get_user")
        self.assertTrue(callable(get_user), "get_user should be a callable")

    def test_get_existing_user(self):
        """Get existing user by id."""
        from lastfm_auth.backend import LastfmBackend
        user = User.objects.create_user(username='test', password='test', email='')
        result = LastfmBackend().get_user(user.id)
        self.assertEqual(result, user)

    def test_get_non_existing_user(self):
        """User ids which don't exist should return none."""
        from lastfm_auth.backend import LastfmBackend
        result = LastfmBackend().get_user(100)
        self.assertEqual(result, None)

    def test_authenticate(self):
        """Authentication backend must define a authenticate method."""
        from lastfm_auth.backend import LastfmBackend
        authenticate = getattr(LastfmBackend, 'authenticate', None)
        self.assertTrue(authenticate, "Auth backend must define authenticate")
        self.assertTrue(callable(authenticate), "authenticate should be a callable")

    def test_authenticate_existing_user(self):
        """Authenticate an existing user."""
        from lastfm_auth.backend import LastfmBackend
        user = User.objects.create_user(username='test', password='test', email='')
        social_user = UserSocialAuth.objects.create(
            user=user, provider='lastfm', uid='1000002'
        )
        response = lastfm_user_response()
        result = LastfmBackend().authenticate(response=response, lastfm=True)
        self.assertEqual(result, user)

    def test_authenticate_non_existing_user(self):
        """Authenticate a new user creating that user."""
        from lastfm_auth.backend import LastfmBackend
        response = lastfm_user_response()
        result = LastfmBackend().authenticate(response=response, lastfm=True)
        self.assertTrue(result)
        if hasattr(result, 'is_new'):
            self.assertTrue(result.is_new)
