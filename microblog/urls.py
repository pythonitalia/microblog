# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *
from microblog import feeds, settings

urlpatterns = patterns('',
    url(
        r'^$',
        'microblog.views.post_list',
        name = 'microblog-full-list'
    ),
    url(
        r'^feeds/(?P<url>.*)/?$',
        'django.contrib.syndication.views.feed',
        {'feed_dict': {'latest': feeds.LatestPosts}}
    ),
    url(
        r'^categories/(?P<category>.*)$',
        'microblog.views.category',
        name = 'microblog-category',
    ),
    url(
        r'^years/(?P<year>\d{4})/$',
        'microblog.views.post_list_by_year',
        name = 'microblog-list-by-year',
    ),
    url(
        r'^years/(?P<year>\d{4})/(?P<month>\d{1,2})/$',
        'microblog.views.post_list_by_year',
        name = 'microblog-list-by-month',
    ),
    url(
        r'^tags/(?P<tag>.*)$',
        'microblog.views.tag',
        name = 'microblog-tag',
    ),
    url(
        r'^authors/(?P<author>.*)$',
        'microblog.views.author',
        name = 'microblog-author',
    ),
)

if settings.MICROBLOG_PINGBACK_SERVER:
    urlpatterns += patterns('',
        (r'^xmlrpc/$', 'django_xmlrpc.views.handle_xmlrpc', {}, 'xmlrpc'),
    )

if settings.MICROBLOG_URL_STYLE == 'date':
    urlpatterns += patterns('',
        url(
            r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\w{1,2})/(?P<slug>[^/]+)/?$',
            'microblog.views.post_detail',
            name = 'microblog-post-detail'
        ),
        url(
            r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\w{1,2})/(?P<slug>[^/]+)/trackback$',
            'microblog.views.trackback_ping',
            name = 'microblog-post-trackback'
        ),
        url(
            r'^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\w{1,2})/(?P<slug>[^/]+)/comment_count$',
            'microblog.views.comment_count',
            name = 'microblog-post-comment-count'
        ),
    )
elif settings.MICROBLOG_URL_STYLE == 'category':
    urlpatterns += patterns('',
        url(
            r'^(?P<category>[^/]+)/(?P<slug>[^/]+)/?$',
            'microblog.views.post_detail',
            name = 'microblog-post-detail'
        ),
        url(
            r'^(?P<category>[^/]+)/(?P<slug>[^/]+)/trackback$',
            'microblog.views.trackback_ping',
            name = 'microblog-post-trackback'
        ),
        url(
            r'^(?P<category>[^/]+)/(?P<slug>[^/]+)/comment_count$',
            'microblog.views.comment_count',
            name = 'microblog-post-comment-count'
        ),
    )
