# -*- coding: UTF-8 -*-
import datetime
from microblog import models, settings
from tagging import models as taggingModels
from django.contrib.auth import models as authModels

from django.conf import settings as dsettings
from django.http import HttpResponse, Http404
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.shortcuts import render_to_response, get_object_or_404

import simplejson
from decorator import decorator

def json(f):
    """
    decoratore da applicare ad una vista per serializzare in json il risultato.
    """
    if dsettings.DEBUG:
        ct = 'text/plain'
        j = lambda d: simplejson.dumps(d, indent = 2)
    else:
        ct = 'application/json'
        j = simplejson.dumps
    def wrapper(func, *args, **kw):
        try:
            result = func(*args, **kw)
        except Exception, e:
            result = j(str(e))
            status = 500
        else:
            if isinstance(result, HttpResponse):
                return result
            else:
                result = j(result)
                status = 200
        return HttpResponse(content = result, content_type = ct, status = status)
    return decorator(wrapper, f)

def category(request, category):
    category = get_object_or_404(models.Category, name = category)
    return render_to_response(
        'microblog/category.html',
        {
            'category': category,
            'posts': category.post_set.all(),
        },
        context_instance = RequestContext(request)
    )

def tag(request, tag):
    tag = get_object_or_404(taggingModels.Tag, name = tag)
    posts = taggingModels.TaggedItem.objects.get_by_model(models.Post, tag)
    return render_to_response(
        'microblog/tag.html',
        {
            'tag': tag,
            'posts': posts,
        },
        context_instance = RequestContext(request)
    )

def author(request, author):
    user = [
        u for u in authModels.User.objects.all()
        if slugify('%s-%s' % (u.first_name, u.last_name)) == author
    ]
    if not user:
        raise Http404()
    else:
        user = user[0]
    posts = models.Post.objects.filter(author = user)
    return render_to_response(
        'microblog/author.html',
        {
            'author': user,
            'posts': posts,
        },
        context_instance = RequestContext(request)
    )

def post_list(request):
    if request.user.is_anonymous():
        posts = models.Post.objects.published()
    else:
        posts = models.Post.objects.all()

    return render_to_response(
        'microblog/post_list.html',
        {
            'object_list': posts
        },
        context_instance = RequestContext(request)
    )
    
def _post_detail(request, content):
    return render_to_response(
        'microblog/post_detail.html',
        {
            'post': content.post,
            'content': content
        },
        context_instance = RequestContext(request)
    )

def _trackback_ping(request, content):
    def success():
        x = ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<response><error>0</error></response>')
        return HttpResponse(content = x, content_type = 'text/xml')

    def failure(message=''):
        x = ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<response><error>1</error><message>%s</message></response>') % message
        return HttpResponse(content = x, content_type = 'text/xml', status = 400)

    if request.method != 'POST':
        return failure('only POST methos is supported')

    if not request.POST.get('url'):
        return failure('url argument is mandatory')

    t = {
        'url': request.POST['url'],
        'blog_name': request.POST.get('blog_name', ''),
        'title': request.POST.get('title', ''),
        'excerpt': request.POST.get('excerpt', ''),
    }
    content.new_trackback(**t)
    return success()

@json
def _comment_count(request, content):
    post = content.post
    if settings.MICROBLOG_COMMENT == 'comment':
        from django.contrib import comments
        from django.contrib.contenttypes.models import ContentType
        model = comments.get_model()
        q = model.objects.filter(
            content_type = ContentType.objects.get_for_model(post),
            object_pk = post.id,
            is_public = True
        )
        return q.count()
    else:
        import httplib2
        from urllib import quote
        h = httplib2.Http()
        params = {
            'forum_api_key': settings.MICROBLOG_COMMENT_DISQUS_FORUM_KEY,
            'url': content.get_url(),
        }
        args = '&'.join('%s=%s' % (k,quote(v)) for k, v in params.items())
        url = settings.MICROBLOG_COMMENT_DISQUS_API_URL + 'get_thread_by_url?%s' % args

        resp, page = h.request(url)
        if resp.status != 200:
            return -1
        page = simplejson.loads(page)
        if not page['succeeded']:
            return -1
        elif page['message'] is None:
            return 0
        else:
            return page['message']['num_comments']

if settings.MICROBLOG_URL_STYLE == 'date':
    def post_detail(request, year, month, day, slug):
        return _post_detail(
            request,
            content = models.PostContent.objects.getBySlugAndDate(slug, year, month, day)
        )

    def trackback_ping(request, year, month, day, slug):
        return _trackback_ping(
            request,
            content = models.PostContent.objects.getBySlugAndDate(slug, year, month, day)
        )

    def comment_count(request, year, month, day, slug):
        return _comment_count(
            request,
            content = models.PostContent.objects.getBySlugAndDate(slug, year, month, day)
        )
elif settings.MICROBLOG_URL_STYLE == 'category':
    def post_detail(request, category, slug):
        return _post_detail(
            request,
            content = models.PostContent.objects.getBySlugAndCategory(slug, category)
        )

    def trackback_ping(request, category, slug):
        return _trackback_ping(
            request,
            content = models.PostContent.objects.getBySlugAndCategory(slug, category)
        )

    @json
    def comment_count(request, category, slug):
        return _comment_count(
            request,
            content = models.PostContent.objects.getBySlugAndCategory(slug, category)
        )
