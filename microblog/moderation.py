# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.core.urlresolvers import reverse
from django.contrib.comments.moderation import CommentModerator, moderator

from models import Post
import settings

import akismet

class PostModeration(CommentModerator):
    #email_notification = True
    enable_field = 'allow_comments'
    auto_moderate_field = 'date'
    moderate_after = 30

    def moderate(self, comment, content_object, request):
        r = super(PostModeration, self).moderate(comment, content_object, request)
        if not r and settings.MICROBLOG_AKISMET_KEY:
            aks = akismet.Akismet(
                agent = 'Microblog',
                key = settings.MICROBLOG_AKISMET_KEY, 
                blog_url = dsettings.DEFAULT_URL_PREFIX + reverse('microblog-full-list')
            )
            try:
                if aks.verify_key():
                    m = request.META
                    data = {
                        'user_ip': m['REMOTE_ADDR'],
                        'user_agent': m.get('HTTP_USER_AGENT', ''),
                        'referrer': m.get('HTTP_REFERER', ''),
                        'comment_type': 'comment',
                        'comment_author': '',
                        'comment_author_email': '',
                        'comment_author_url': '',
                        'HTTP_ACCEPT': '',
                        'permalink': '',
                        'SERVER_NAME': '',
                        'SERVER_SOFTWARE': '',
                        'SERVER_ADMIN': '',
                        'SERVER_ADDR': '',
                        'SERVER_SIGNATURE': '',
                        'SERVER_PORT': '',
                    }
                    r = aks.comment_check(comment.comment.encode('utf-8'), data, build_data = False)
                    print 'x', r, data
                elif dsettings.DEBUG:
                    raise ValueError('Akismet: invalid key')
            except:
                if dsettings.DEBUG:
                    raise
                pass
        return r

moderator.register(Post, PostModeration)
