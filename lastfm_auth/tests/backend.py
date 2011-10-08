from StringIO import StringIO
from urlparse import urlparse, parse_qs
from urllib2 import URLError

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
        self.assertEqual('%s://%s%s' % (scheme, netloc, path), 'https://www.last.fm/api/auth/')
        query_data = parse_qs(query)
        self.assertEqual(query_data['api_key'][0], settings.LASTFM_API_KEY)

    def test_callback(self):
        """Check callback sent to Last.fm."""
        response = self.client.get(self.login_url)
        url = response['Location']
        scheme, netloc, path, params, query, fragment = urlparse(url)
        query_data = parse_qs(query)
        callback = reverse(COMPLETE_URL_NAME, kwargs={'backend': 'lastfm'})
        self.assertTrue(query_data['cb'][0].endswith(callback))
        self.assertTrue(query_data['cb'][0].startswith('http:'))

    def test_https_callback(self):
        """
        Convert https callbacks to http due to Last.fm bug.
        See http://www.last.fm/group/Last.fm+Web+Services/forum/21604/_/633280
        """
        response = self.client.get(self.login_url, **{'wsgi.url_scheme': 'https'})
        url = response['Location']
        scheme, netloc, path, params, query, fragment = urlparse(url)
        query_data = parse_qs(query)
        callback = reverse(COMPLETE_URL_NAME, kwargs={'backend': 'lastfm'})
        self.assertTrue(query_data['cb'][0].startswith('http:'))


class AuthCompleteTestCase(DjangoTestCase):
    """Complete login process from Last.fm."""

    def setUp(self):
        self.complete_url = reverse(COMPLETE_URL_NAME, kwargs={'backend': 'lastfm'})
        self.access_token_patch = mock.patch('lastfm_auth.backend.LastfmAuth.access_token')
        self.access_token_mock = self.access_token_patch.start()
        self.access_token_mock.return_value = ('USERNAME', 'FAKETOKEN')
        self.user_data_patch = mock.patch('lastfm_auth.backend.LastfmAuth.user_data')
        self.user_data_mock = self.user_data_patch.start()
        fake_data = lastfm_user_response()
        self.user_data_mock.return_value = fake_data

    def tearDown(self):
        self.access_token_patch.stop()
        self.user_data_patch.stop()

    def test_new_user(self):
        """Login for the first time via Last.fm."""
        data = {'token': 'FAKEKEY'}
        response = self.client.get(self.complete_url, data)
        self.assertRedirects(response, NEW_USER_REDIRECT)

    def test_new_user_name(self):
        """Check the name set on the newly created user."""
        data = {'token': 'FAKEKEY'}
        self.client.get(self.complete_url, data)
        new_user = User.objects.latest('id')
        self.assertEqual(new_user.first_name, "Richard")
        self.assertEqual(new_user.last_name, "Jones")

    def test_single_name(self):
        """Process a user with a single word name."""
        fake_data = lastfm_user_response()
        fake_data['realname'] = "Cher"
        self.user_data_mock.return_value = fake_data
        data = {'token': 'FAKEKEY'}
        self.client.get(self.complete_url, data)
        new_user = User.objects.latest('id')
        self.assertEqual(new_user.first_name, "Cher")
        self.assertEqual(new_user.last_name, "")

    def test_existing_user(self):
        """Login with an existing user via Last.fm."""
        user = User.objects.create_user(username='test', password='test', email='')
        social_user = UserSocialAuth.objects.create(
            user=user, provider='lastfm', uid='1000002'
        )
        data = {'token': 'FAKEKEY'}
        response = self.client.get(self.complete_url, data)
        self.assertRedirects(response, DEFAULT_REDIRECT)

    def test_failed_authentication(self):
        """Failed authentication. Bad data from Last.fm."""
        self.user_data_mock.return_value = None
        data = {'token': 'FAKEKEY'}
        response = self.client.get(self.complete_url, data)
        self.assertRedirects(response, LOGIN_ERROR_URL)

    def test_no_token(self):
        """Failed auth due to no token."""
        response = self.client.get(self.complete_url)
        self.assertRedirects(response, LOGIN_ERROR_URL)


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
        if hasattr(result, 'is_new'):
            self.assertFalse(result.is_new)

    def test_authenticate_non_existing_user(self):
        """Authenticate a new user creating that user."""
        from lastfm_auth.backend import LastfmBackend
        response = lastfm_user_response()
        result = LastfmBackend().authenticate(response=response, lastfm=True)
        self.assertTrue(result)
        if hasattr(result, 'is_new'):
            self.assertTrue(result.is_new)


class LastfmAPITestCase(DjangoTestCase):
    """Validate calls to the Last.fm API."""

    def test_access_token_url(self):
        """
        Check url contruction for requesting access/session token.
        See http://www.last.fm/api/show?service=125
        """
        from lastfm_auth.backend import LastfmAuth
        with mock.patch('lastfm_auth.backend.urlopen') as urlopen:
            urlopen.return_value = StringIO('')
            request = mock.MagicMock()
            redirect = 'http://example.com'
            access_token = LastfmAuth(request, redirect).access_token('REQUESTTOKEN')
            args, kwargs = urlopen.call_args
            url = args[0]
            scheme, netloc, path, params, query, fragment = urlparse(url)
            self.assertEqual('%s://%s%s' % (scheme, netloc, path), 'https://ws.audioscrobbler.com/2.0/')
            query_data = parse_qs(query)
            self.assertEqual(query_data['api_key'][0], settings.LASTFM_API_KEY)
            self.assertEqual(query_data['token'][0], 'REQUESTTOKEN')
            self.assertEqual(query_data['method'][0], 'auth.getSession')
            self.assertEqual(query_data['format'][0], 'json')

    def test_access_token_value(self):
        """
        Check parsed access token value.
        See http://www.last.fm/api/show?service=125
        """
        from lastfm_auth.backend import LastfmAuth
        with mock.patch('lastfm_auth.backend.urlopen') as urlopen:
            return_data = {
                'session': {
                    'name': 'MyLastFMUsername',
                    'key': 'd580d57f32848f5dcf574d1ce18d78b2',
                    'subscriber': 0,
                }
            }
            urlopen.return_value = StringIO(simplejson.dumps(return_data))
            request = mock.MagicMock()
            redirect = 'http://example.com'
            username, access_token = LastfmAuth(request, redirect).access_token('REQUESTTOKEN')
            self.assertEqual(username, 'MyLastFMUsername')
            self.assertEqual(access_token, 'd580d57f32848f5dcf574d1ce18d78b2')

    def test_access_token_upstream_failure(self):
        """
        Check handling upstream failures from Last.fm.
        See http://www.last.fm/api/show?service=125
        """
        from lastfm_auth.backend import LastfmAuth
        
        with mock.patch('lastfm_auth.backend.urlopen') as urlopen:
            urlopen.side_effect = URLError('Fake URL error')
            request = mock.MagicMock()
            redirect = 'http://example.com'
            username, access_token = LastfmAuth(request, redirect).access_token('REQUESTTOKEN')
            self.assertFalse(username)
            self.assertFalse(access_token)

    def test_access_token_bad_data(self):
        """
        Handle bad data when requesting access/session token.
        See http://www.last.fm/api/show?service=125
        """
        from lastfm_auth.backend import LastfmAuth
        with mock.patch('lastfm_auth.backend.urlopen') as urlopen:
            urlopen.return_value = StringIO('')
            request = mock.MagicMock()
            redirect = 'http://example.com'
            username, access_token = LastfmAuth(request, redirect).access_token('REQUESTTOKEN')
            self.assertFalse(username)
            self.assertFalse(access_token)

    def test_user_data_url(self):
        """
        Check url contruction for requesting user data.
        See http://www.last.fm/api/show?service=344
        """
        from lastfm_auth.backend import LastfmAuth
        with mock.patch('lastfm_auth.backend.urlopen') as urlopen:
            urlopen.return_value = StringIO('')
            request = mock.MagicMock()
            redirect = 'http://example.com'
            user_data = LastfmAuth(request, redirect).user_data('UserName')
            args, kwargs = urlopen.call_args
            url = args[0]
            scheme, netloc, path, params, query, fragment = urlparse(url)
            self.assertEqual('%s://%s%s' % (scheme, netloc, path), 'https://ws.audioscrobbler.com/2.0/')
            query_data = parse_qs(query)
            self.assertEqual(query_data['api_key'][0], settings.LASTFM_API_KEY)
            self.assertEqual(query_data['method'][0], 'user.getinfo')
            self.assertEqual(query_data['format'][0], 'json')

    def test_user_data_value(self):
        """
        Check return value for requesting user data.
        See http://www.last.fm/api/show?service=344
        """
        from lastfm_auth.backend import LastfmAuth
        with mock.patch('lastfm_auth.backend.urlopen') as urlopen:
            return_data = {'user': lastfm_user_response()}
            urlopen.return_value = StringIO(simplejson.dumps(return_data))
            request = mock.MagicMock()
            redirect = 'http://example.com'
            user_data = LastfmAuth(request, redirect).user_data('UserName')
            self.assertEqual(user_data, lastfm_user_response())

    def test_user_data_upstream_failure(self):
        """
        Handle upstream errors when requesting user data.
        See http://www.last.fm/api/show?service=344
        """
        from lastfm_auth.backend import LastfmAuth
        with mock.patch('lastfm_auth.backend.urlopen') as urlopen:
            urlopen.side_effect = URLError('Fake URL error')
            request = mock.MagicMock()
            redirect = 'http://example.com'
            user_data = LastfmAuth(request, redirect).user_data('UserName')
            self.assertEqual(user_data, None)

    def test_user_data_bad_data(self):
        """
        Bad return data when requesting user data.
        See http://www.last.fm/api/show?service=344
        """
        from lastfm_auth.backend import LastfmAuth
        with mock.patch('lastfm_auth.backend.urlopen') as urlopen:
            urlopen.return_value = StringIO('')
            request = mock.MagicMock()
            redirect = 'http://example.com'
            user_data = LastfmAuth(request, redirect).user_data('UserName')
            self.assertEqual(user_data, None)
