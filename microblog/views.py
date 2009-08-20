import datetime
from microblog import models

from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404

def post_detail(request, year, month, day, slug):
    postcontent = get_object_or_404(
        models.PostContent, 
        slug = slug, 
        post__date__year = int(year),
        post__date__month = int(month),
        post__date__day = int(day)
    )
    return render_to_response(
        'microblog/post_detail.html',
        {
            'post': postcontent.post,
            'content': postcontent
        },
        context_instance = RequestContext(request)
    )

def trackback_ping(request, year, month, day, slug):
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

    postcontent = get_object_or_404(
        models.PostContent, 
        slug = slug, 
        post__date__year = int(year),
        post__date__month = int(month),
        post__date__day = int(day)
    )
    post = postcontent.post
    t = {
        'url': request.POST['url'],
        'blog_name': request.POST.get('blog_name', ''),
        'title': request.POST.get('title', ''),
        'excerpt': request.POST.get('excerpt', ''),
    }
    post.new_trackback(**t)
    return success()
