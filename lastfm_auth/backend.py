"""
Last.fm support for Django-Social-Auth.

An application must be registered first on Last.fm and the settings LASTFM_API_KEY
and LASTFM_SECRET must be defined with they corresponding values.
"""

from hashlib import md5
from urllib import urlencode
from urllib2 import urlopen

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import simplejson

from social_auth.backends import BaseAuth, SocialAuthBackend, USERNAME


LASTFM_API_SERVER = 'https://ws.audioscrobbler.com/2.0/'
LASTFM_AUTHORIZATION_URL = 'https://www.last.fm/api/auth/'


class LastfmBackend(SocialAuthBackend):
    """Last.fm authentication backend."""
    name = "lastfm"
    EXTRA_DATA = [('id', 'id'), ]

    def get_user_id(self, details, response):
        """Get unique User id from response"""
        return response['id']

    def get_user_details(self, response):
        """Return user details from Last.fm account"""
        full_name = response['realname'].strip()
        if len(full_name.split(' ')) > 1:
            last_name = full_name.split(' ')[-1].strip()
            first_name = full_name.replace(last_name, '').strip()
        else:
            first_name = full_name
            last_name = ''
        data = {
            USERNAME: response.get('name', ''),
            'email': '',
            'fullname': full_name,
            'first_name': first_name,
            'last_name': last_name
        }
        return data

    def extra_data(self, user, uid, response, details):
        data = {'access_token': response.get('access_token', '')}
        name = self.name.replace('-', '_').upper()
        names = (self.EXTRA_DATA or []) + getattr(settings, name + '_EXTRA_DATA', [])
        data.update((alias, response.get(name)) for name, alias in names)
        return data


class LastfmAuth(BaseAuth):
    """Last.fm authentication mechanism."""
    AUTH_BACKEND = LastfmBackend
    SETTINGS_KEY_NAME = 'LASTFM_API_KEY'
    SETTINGS_SECRET_NAME = 'LASTFM_SECRET'

    def auth_url(self):
        """Return authorization redirect url."""
        key = self.api_key()
        query = urlencode({'api_key': key})
        return '%s?%s' % (LASTFM_AUTHORIZATION_URL, query)

    def auth_complete(self, *args, **kwargs):
        """Return user from authenticate."""
        token = self.data.get('token')
        if not token:
            raise ValueError('No token returned')

        username, access_token = self.access_token(token)
        data = self.user_data(username)
        if data is not None:
            data['access_token'] = access_token

        kwargs.update({'response': data, self.AUTH_BACKEND.name: True})
        return authenticate(*args, **kwargs)

    def access_token(self, token):
        """Get the Last.fm session/access token via auth.getSession.""" 
        data = {
            'method': 'auth.getSession',
            'api_key': self.api_key(),
            'token': token,
            'api_sig': self.method_signature('auth.getSession', token),
            'format': 'json',
        }
        query = urlencode(data)
        url = '%s?%s' % (LASTFM_API_SERVER, query)
        try:
            response = urlopen(url).read()
            session = simplejson.loads(response)['session']
            access_token = session['key']
            username = session['name']
        except:
            access_token = ''
            username = ''
        return (username, access_token)

    def user_data(self, username):
        """Request user data."""
        data = {
            'method': 'user.getinfo',
            'api_key': self.api_key(),
            'user': username,
            'format': 'json',
        }
        query = urlencode(data)
        url = '%s?%s' % (LASTFM_API_SERVER, query)
        try:
            response = urlopen(url).read()
            user_data = simplejson.loads(response)['user']
        except:
            user_data = None
        return user_data

    def method_signature(self, method, token):
        """Generate method signature for API calls."""
        data = {
            'key': self.api_key(),
            'secret': self.secret_key(),
            'method': method,
            'token': token,
        }
        key = 'api_key%(key)smethod%(method)stoken%(token)s%(secret)s' % data
        return md5(key).hexdigest()

    @classmethod
    def enabled(cls):
        """Enable only if settings are defined."""
        return cls.api_key and cls.secret_key

    @classmethod
    def api_key(cls):
        return getattr(settings, cls.SETTINGS_KEY_NAME, '')

    @classmethod
    def secret_key(cls):
        return getattr(settings, cls.SETTINGS_SECRET_NAME, '')


# Backend definition
BACKENDS = {
    'lastfm': LastfmAuth,
}
