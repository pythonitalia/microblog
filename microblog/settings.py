# -*- coding: UTF-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if not settings.LANGUAGES:
    raise ImproperlyConfigured('You need at least one entry in the LANGUAGES settings')   

# Default language for the blog posts
MICROBLOG_DEFAULT_LANGUAGE = getattr(
    settings, 'MICROBLOG_DEFAULT_LANGUAGE', 
    settings.LANGUAGES[0][0])

# url style for microblog posts. date or category
MICROBLOG_URL_STYLE = getattr(settings, 'MICROBLOG_URL_STYLE', 'date')
assert MICROBLOG_URL_STYLE in ('date', 'category'), "MICROBLOG_URL_STYLE should be either date or category"

MICROBLOG_LANGUAGE_FALLBACK_ON_POST_LIST = getattr(settings, 'MICROBLOG_LANGUAGE_FALLBACK_ON_POST_LIST', False)

# enable/disable the server side support for the trackback protocol
MICROBLOG_TRACKBACK_SERVER = getattr(settings, 'MICROBLOG_TRACKBACK_SERVER', True)

# enable/disable the server side support for the pingback protocol
MICROBLOG_PINGBACK_SERVER = getattr(settings, 'MICROBLOG_PINGBACK_SERVER', True)
if MICROBLOG_PINGBACK_SERVER:
    from pingback import create_ping_func
    from django_xmlrpc import xmlrpcdispatcher

    if MICROBLOG_URL_STYLE == 'date':
        def url_handler(year, month, day, slug):
            from microblog import models
            return models.PostContent.objects.getBySlugAndDate(slug, year, month, day)
    elif MICROBLOG_URL_STYLE == 'category':
        def url_handler(category, slug):
            from microblog import models
            return models.PostContent.objects.getBySlugAndCategory(slug, category)

    details = { 'microblog-post-detail': url_handler }
    xmlrpcdispatcher.register_function(create_ping_func(**details), 'pingback.ping')

MICROBLOG_TITLE = getattr(settings, 'MICROBLOG_TITLE', 'My Microblog')
MICROBLOG_DESCRIPTION = getattr(settings, 'MICROBLOG_DESCRIPTION', '')

# configure the moderation system:
# None - moderation disabled
# light - auto moderate comments after 30 days and sends email 
# akismet - light + akismet validation
# always - always moderate
MICROBLOG_MODERATION_TYPE = getattr(settings, 'MICROBLOG_MODERATION_TYPE', 'light')
MICROBLOG_AKISMET_KEY = getattr(settings, 'MICROBLOG_AKISMET_KEY', None)
if MICROBLOG_MODERATION_TYPE == 'akismet' and not MICROBLOG_AKISMET_KEY:
    raise ImproperlyConfigured('please set your akismet key')
elif MICROBLOG_AKISMET_KEY:
    try:
        import akismet
    except ImportError:
        raise ImproperlyConfigured('In order to use the akismet service you need the akismet module')

if hasattr(settings, 'MICROBLOG_ENABLE_MODERATION'):
    print 'warning, MICROBLOG_ENABLE_MODERATION is deprecated, use MICROBLOG_MODERATION_TYPE instead'
    if settings.MICROBLOG_ENABLE_MODERATION:
        if settings.MICROBLOG_AKISMET_KEY:
            MICROBLOG_MODERATION_TYPE = 'akismet'
        else:
            MICROBLOG_MODERATION_TYPE = 'light'
    else:
        MICROBLOG_MODERATION_TYPE = None
# Microblog twitter integration configuration

# Enable the twitter integration (True or False)
MICROBLOG_TWITTER_INTEGRATION = getattr(settings, 'MICROBLOG_TWITTER_INTEGRATION', False)

# String containing the twitter account username
MICROBLOG_TWITTER_USERNAME = getattr(settings, 'MICROBLOG_TWITTER_USERNAME', None)

# String containing the twitter account password
MICROBLOG_TWITTER_PASSWORD = getattr(settings, 'MICROBLOG_TWITTER_PASSWORD', None)

# String containing the template (django template language) of the message for new blogposts
# You can use {{ title }} and {{ url }} tags
MICROBLOG_TWITTER_MESSAGE_TEMPLATE_NEW_POST = getattr(settings, 'MICROBLOG_TWITTER_MESSAGE_TEMPLATE_NEW_POST', 'New blogpost: {{ content.headline }} ( {{ url }} )')

# String containing the template (django template language) of the message for updated blogposts
# You can use {{ title }} and {{ url }} tags
MICROBLOG_TWITTER_MESSAGE_TEMPLATE_UPDATED_POST = getattr(settings, 'MICROBLOG_TWITTER_MESSAGE_TEMPLATE_UPDATED_POST', 'Updated blogpost: {{content.headline }} ( {{ url }} )')

# String containin the language code
# eg. "en" or "it"
MICROBLOG_TWITTER_POST_LANGUAGE = getattr(settings, 'MICROBLOG_TWITTER_POST_LANGUAGE', MICROBLOG_DEFAULT_LANGUAGE)

# Callable that mangle the given url
MICROBLOG_TWITTER_POST_URL_MANGLER = getattr(settings, 'MICROBLOG_TWITTER_POST_URL_MANGLER', lambda p: p.get_url())

# Enable the pagination for posts in the post list pages
MICROBLOG_POST_LIST_PAGINATION = getattr(settings, 'MICROBLOG_POST_LIST_PAGINATION', False)

# Number of post in a single page
MICROBLOG_POST_PER_PAGE = getattr(settings, 'MICROBLOG_POST_PER_PAGE', 0)
