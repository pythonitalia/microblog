# -*- coding: UTF-8 -*-
import datetime
from microblog import models, settings
from tagging import models as taggingModels
from django.contrib.auth import models as authModels

from django.conf import settings as dsettings
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify

from django.core.paginator import Paginator, InvalidPage, EmptyPage

try:
    import json as simplejson
except ImportError:
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
    post_list = _posts_list(request, featured=None).filter(category=category)
    post_list_count = post_list.count()
    posts = _paginate_posts(post_list, request)

    return render_to_response(
        'microblog/category.html',
        {
            'category': category,
            'posts': posts,
            'post_count': post_list_count,
        },
        context_instance = RequestContext(request)
    )

def post_list_by_year(request, year, month=None):
    post_list = _posts_list(request).filter(date__year=year)
    if month is not None:
        post_list = post_list.filter(date__month=month)
    post_list_count = post_list.count()
    posts = _paginate_posts(post_list, request)

    return render_to_response(
        'microblog/list_by_year.html',
        {
            'year': year,
            'month': month,
            'posts': posts,
            'post_count': post_list_count,
        },
        context_instance = RequestContext(request)
    )

def tag(request, tag):
    tag = get_object_or_404(taggingModels.Tag, name = tag)
    post_list = _posts_list(request, featured=None)
    tagged_posts = taggingModels.TaggedItem.objects.get_by_model(post_list, tag)
    post_list_count = tagged_posts.count()
    posts = _paginate_posts(tagged_posts, request)
    return render_to_response(
        'microblog/tag.html',
        {
            'tag': tag,
            'posts': posts,
            'post_count': post_list_count,
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
    post_list = _posts_list(request).filter(author = user)
    post_list_count = post_list.count()
    posts = _paginate_posts(post_list, request)
    return render_to_response(
        'microblog/author.html',
        {
            'author': user,
            'posts': posts,
            'post_count': post_list_count,
        },
        context_instance = RequestContext(request)
    )

def post_list(request):
    posts = _posts_list(request)
    return render_to_response(
        'microblog/post_list.html',
        {
            'posts': _paginate_posts(posts, request),
            'featured': models.Post.objects.featured(),
        },
        context_instance = RequestContext(request)
    )

def _paginate_posts(post_list, request):
    if settings.MICROBLOG_POST_LIST_PAGINATION:
        paginator = Paginator(post_list, settings.MICROBLOG_POST_PER_PAGE)
        try:
            page = int(request.GET.get("page", "1"))
        except ValueError:
            page = 1

        try:
            posts = paginator.page(page)
        except (EmptyPage, InvalidPage):
            posts = paginator.page(1)
    else:
        paginator = Paginator(post_list, len(post_list) or 1)
        posts = paginator.page(1)

    return posts

def _posts_list(request, featured=False):
    if settings.MICROBLOG_LANGUAGE_FALLBACK_ON_POST_LIST:
        lang = None
    else:
        lang = request.LANGUAGE_CODE

    post_list = models.Post.objects.published(lang=lang, user=request.user)
    if not featured:
        return post_list
    return models.Post.objects.filterPostsByFeaturedStatus(post_list, featured=featured)

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

def _post404(f):
    def wrapper(*args, **kw):
        try:
            return f(*args, **kw)
        except models.PostContent.DoesNotExist:
            raise Http404()
    return wrapper

if settings.MICROBLOG_URL_STYLE == 'date':
    @_post404
    def post_detail(request, year, month, day, slug):
        return _post_detail(
            request,
            content = models.PostContent.objects.getBySlugAndDate(slug, year, month, day)
        )

    @_post404
    def trackback_ping(request, year, month, day, slug):
        return _trackback_ping(
            request,
            content = models.PostContent.objects.getBySlugAndDate(slug, year, month, day)
        )

    @_post404
    def comment_count(request, year, month, day, slug):
        return _comment_count(
            request,
            content = models.PostContent.objects.getBySlugAndDate(slug, year, month, day)
        )
elif settings.MICROBLOG_URL_STYLE == 'category':
    @_post404
    def post_detail(request, category, slug):
        return _post_detail(
            request,
            content = models.PostContent.objects.getBySlugAndCategory(slug, category)
        )

    @_post404
    def trackback_ping(request, category, slug):
        return _trackback_ping(
            request,
            content = models.PostContent.objects.getBySlugAndCategory(slug, category)
        )

    @_post404
    def comment_count(request, category, slug):
        return _comment_count(
            request,
            content = models.PostContent.objects.getBySlugAndCategory(slug, category)
        )
