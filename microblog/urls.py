# -*- coding: UTF-8 -*-
from django.conf.urls.defaults import *
from microblog import views, models, feeds, settings

urlpatterns = patterns('',
    url(
        r'^$',
        'django.views.generic.list_detail.object_list',
        {
            'queryset': models.Post.objects.all()
        },
        name = 'microblog-full-list'
    ),
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
    (r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': {'latest': feeds.LatestPosts}}),
)

if settings.MICROBLOG_COMMENT == 'comment':
    urlpatterns += patterns('',
        (r'^comments/', include('django.contrib.comments.urls')),
    )

if settings.MICROBLOG_PINGBACK_SERVER:
    urlpatterns += patterns('',
        (r'^xmlrpc/$', 'django_xmlrpc.views.handle_xmlrpc', {}, 'xmlrpc'),
    )
