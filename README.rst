Django-Lastfm-Auth
==============================

Django-Lastfm-Auth is an extension to `Django-Social-Auth <https://github.com/omab/django-social-auth>`_
which adds a backend for Last.fm.

If you are looking for a stand alone Last.fm authentication backend then please
check out `django-lastfmauth <http://pypi.python.org/pypi/django-lastfmauth/>`_.


Requirements
-------------------------------

- Django-Social-Auth >= 0.3.3
    - Django >= 1.2.5
    - Python-OAuth2 >= 1.5.167
    - Python-Openid >= 2.2


API Keys
-------------------------------

In order to use this application you must sign up for API keys on
Last.fm. These should be put into your settings file using the settings::

    LASTFM_API_KEY = '' # Your api key
    LASTFM_SECRET = '' # Your api secret


Extra data
-------------------------------

Similar to the other OAuth backends you can define

    LASTFM_EXTRA_DATA = [('realname', 'realname'), ]

as a list of tuples (response name, alias) to store on the UserSocialAuth model.


Installation
-------------------------------

To install django-lastfm-auth via pip::

    pip install django-lastfm-auth

Or you can from the latest version from Github manually::

    git clone git://github.com/mlavin/django-lastfm-auth.git
    cd django-lastfm-auth
    python setup.py install

or via pip::

    pip install -e git+https://github.com/mlavin/django-lastfm-auth.git

Once you have the app installed you must include in your settings::

    INSTALLED_APPS = (
        ...
        'social_auth',
        'lastfm_auth',
        ...
    )

    AUTHENTICATION_BACKENDS = (
        ...
        'lastfm_auth.backend.LastfmBackend',
        ...
    )

    SOCIAL_AUTH_IMPORT_BACKENDS = (
        ...
        'lastfm_auth',
        ...    
    )

Please refer to the `Django-Social-Auth <http://django-social-auth.readthedocs.org/>`_
documentation for additional information.


Questions or Issues?
-------------------------------

If you have questions, issues or requests for improvements please let me know on
`Github <https://github.com/mlavin/django-lastfm-auth/issues>`_.
