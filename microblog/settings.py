# -*- coding: UTF-8 -*-
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

if not settings.LANGUAGES:
    raise ImproperlyConfigured('You need at least one entry in the LANGUAGES settings')   

# Default language for the blog posts
MICROBLOG_DEFAULT_LANGUAGE = getattr(
    settings, 'MICROBLOG_DEFAULT_LANGUAGE', 
    settings.LANGUAGES[0][0])

# enable/disable the server side support for the trackback protocol
MICROBLOG_TRACKBACK_SERVER = getattr(settings, 'MICROBLOG_TRACKBACK_SERVER', True)

# enable/disable the server side support for the pingback protocol
MICROBLOG_PINGBACK_SERVER = getattr(settings, 'MICROBLOG_PINGBACK_SERVER', True)

if MICROBLOG_PINGBACK_SERVER:
    from pingback import create_ping_func
    from django_xmlrpc import xmlrpcdispatcher

    def url_handler(year, month, day, slug):
        from microblog import models
        return models.PostContent.objects.getBySlugAndDate(slug, year, month, day)
    details = { 'microblog-post-detail': url_handler }
    xmlrpcdispatcher.register_function(create_ping_func(**details), 'pingback.ping')

MICROBLOG_TITLE = getattr(settings, 'MICROBLOG_TITLE', 'My Microblog')
MICROBLOG_DESCRIPTION = getattr(settings, 'MICROBLOG_DESCRIPTION', '')

# select the comment system: comment (django) or disqus
MICROBLOG_COMMENT = getattr(settings, 'MICROBLOG_COMMENT', 'comment')

# Disqus embed code
MICROBLOG_COMMENT_DISQUS_EMBED = getattr(settings, 'MICROBLOG_COMMENT_DISQUS_EMBED', '')

# forum key code (needed to enable comments count)
MICROBLOG_COMMENT_DISQUS_FORUM_KEY = getattr(settings, 'MICROBLOG_COMMENT_DISQUS_FORUM_KEY', None)

MICROBLOG_COMMENT_DISQUS_API_URL = 'http://disqus.com/api/'

