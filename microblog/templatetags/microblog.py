# -*- coding: UTF-8 -*-
from __future__ import absolute_import
import re
from django import template
from django.db.models import Count
from django.conf import settings as dsettings
from django.contrib.sites.models import Site
from django.template.loader import render_to_string
from microblog import models
from microblog import settings
from random import randint

register = template.Library()

class LastBlogPost(template.Node):
    def __init__(self, limit, var_name):
        self.var_name = var_name
        self.limit = limit

    def render(self, context):
        query = models.Post.objects.published()
        if self.limit:
            query = query[:self.limit]
        lang = context.get('LANGUAGE_CODE', settings.MICROBLOG_DEFAULT_LANGUAGE)
        posts = [ (p, p.content(lang)) for p in query ]
        context[self.var_name] = posts
        return ''
        
@register.tag
def last_blog_post(parser, token):
    contents = token.split_contents()
    tag_name = contents[0]
    limit = None
    try:
        if contents[1] != 'as':
            try:
                limit = int(contents[1])
            except (ValueError, TypeError):
                raise template.TemplateSyntaxError("%r tag argument should be an integer" % tag_name)
        else:
            limit = None
        if contents[-2] != 'as':
            raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
        var_name = contents[-1]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    return LastBlogPost(limit, var_name)

@register.tag
def category_list(parser, token):
    """
    {% category_list ["include-empty"] as var_name %}
    """
    class Categories(template.Node):
        def __init__(self, include_empty, var_name):
            self.include_empty = bool(include_empty)
            self.var_name = var_name
        def render(self, context):
            c = models.Category.objects.all().order_by('name')
            if not self.include_empty:
                c = c.annotate(count = Count('post')).filter(count__gt = 0)
            context[self.var_name] = c
            return ''

    contents = token.split_contents()
    tag_name = contents.pop(0)
    if len(contents) > 2:
        if contents.pop(0) != '"include-empty"':
            raise template.TemplateSyntaxError("%r tag argument should be \"include-empty\"" % tag_name)
        empty = True
    else:
        empty = False
            
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    return Categories(empty, var_name)

@register.inclusion_tag('microblog/show_post_summary.html', takes_context=True)
def show_post_summary(context, post):
    request = context['request']
    if context['user'].is_anonymous() and not post.is_published():
        return {}
    lang = context['LANGUAGE_CODE']
    contents = dict((c.language, c) for c in post.postcontent_set.all())
    try:
        content = contents[lang]
        if not content.headline:
            raise KeyError()
    except KeyError:
        for l, c in contents.items():
            if c.headline:
                content = c
                break
        else:
            raise ValueError('There is no a valid content (in any language)')
    return {
        'post': post,
        'content': content,
        'MEDIA_URL': context['MEDIA_URL'],
        'request': request,
    }

@register.inclusion_tag('microblog/show_post_detail.html', takes_context=True)
def show_post_detail(context, content, options=None):
    request = context['request']
    if context['user'].is_anonymous() and not content.post.is_published():
        return {}
    return {
        'post': content.post,
        'options': options,
        'content': content,
        'MEDIA_URL': context['MEDIA_URL'],
        'request': request,
    }

class DjangoComments(template.Node):
    def __init__(self, content):
        self.content = template.Variable(content)

    def render(self, context):
        content = self.content.resolve(context)
        return render_to_string(
            'microblog/show_django_comments.html',
            {
                'content': content,
                'post': content.post,
            }
        )

class DisqusComments(template.Node):
    def __init__(self, content):
        self.content = template.Variable(content)

    def render(self, context):
        content = self.content.resolve(context)
        return render_to_string(
            'microblog/show_disqus_comments.html',
            {
                'content': content,
                'post': content.post,
                'embed': settings.MICROBLOG_COMMENT_DISQUS_EMBED,
                'debug': dsettings.DEBUG,
            }
        )

@register.tag
def show_post_comments(parser, token):
    contents = token.split_contents()
    tag_name = contents.pop(0)
    content  = contents.pop(0)
    if contents:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    if settings.MICROBLOG_COMMENT == 'comment':
        comment = DjangoComments(content)
    else:
        comment = DisqusComments(content)
    return comment

class DjangoCountComments(template.Node):
    def __init__(self, content):
        self.content = template.Variable(content)

    def render(self, context):
        content = self.content.resolve(context)
        return render_to_string(
            'microblog/show_django_count_comments.html',
            {
                'content': content,
                'post': post,
            }
        ).strip()

class DisqusCountComments(template.Node):
    def __init__(self, content):
        self.content = template.Variable(content)

    def render(self, context):
        content = self.content.resolve(context)
        return render_to_string(
            'microblog/show_disqus_count_comments.html',
            {
                'content': content,
                'post': content.post,
                'forum_key': settings.MICROBLOG_COMMENT_DISQUS_FORUM_KEY,
                'random_id': 'i%s' % (randint(0, 100000), ),
            }
        ).strip()

@register.tag
def show_post_comment_count(parser, token):
    contents = token.split_contents()
    tag_name = contents[0]
    try:
        content = contents[1]
    except IndexError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    if settings.MICROBLOG_COMMENT == 'comment':
        counter = DjangoCountComments(content)
    else:
        counter = DisqusCountComments(content)
    return counter

@register.inclusion_tag('microblog/show_social_networks.html', takes_context=True)
def show_social_networks(context, content):
    request = context['request']
    site = Site.objects.get_current()
    return {
        'post': content.post,
        'content': content,
        'content_url': 'http://%s%s' % (site.domain, content.get_absolute_url()),
        'MEDIA_URL': context['MEDIA_URL'],
        'request': request,
    }

@register.inclusion_tag('microblog/trackback_rdf.xml')
def trackback_rdf(content):
    return {
        'content': content if settings.MICROBLOG_TRACKBACK_SERVER else None,
    }

@register.inclusion_tag('microblog/show_reactions_list.html')
def show_reactions_list(content):
    trackbacks = content.trackback_set.all()
    if settings.MICROBLOG_PINGBACK_SERVER:
        from pingback.models import Pingback
        pingbacks = Pingback.objects.pingbacks_for_object(content).filter(approved = True)
    else:
        pingbacks = []
    reactions = sorted(list(trackbacks) + list(pingbacks), key = lambda r: r.date, reverse = True)
    for ix, r in enumerate(reactions):
        if not hasattr(r, 'excerpt'):
            r.excerpt = r.content
    return {
        'reactions': reactions,
    }

class PostContent(template.Node):
    def __init__(self, arg, var_name):
        try:
            self.pid = int(arg)
        except ValueError:
            self.pid = template.Variable(arg)
        self.var_name = var_name

    def render(self, context):
        try:
            pid = self.pid.resolve(context)
        except AttributeError:
            pid = self.pid
        except template.VariableDoesNotExist:
            pid = None
        if pid:
            dlang = settings.MICROBLOG_DEFAULT_LANGUAGE
            lang = context.get('LANGUAGE_CODE', dlang)
            contents = dict((c.language, c) for c in models.PostContent.objects.filter(post = pid))
            for l in (lang, dlang) + tuple(contents.keys()):
                try:
                    content = contents[l]
                except KeyError:
                    continue
                if content.body:
                    break
            else:
                content = None
        else:
            content = None
        context[self.var_name] = content
        return ""

@register.tag
def get_post_content(parser, token):
    contents = token.split_contents()
    try:
        tag_name, arg, _, var_name = contents
    except ValueError:
        raise template.TemplateSyntaxError("%r tag's argument should be an integer" % contents[0])
    return PostContent(arg, var_name)


last_close = re.compile(r'(</[^>]+>)$')

@register.filter
def prepare_summary(postcontent):
    """
    Aggiunge al summary il link continua che punta al body del post
    """
    if not postcontent.body:
        return postcontent.summary
    summary = postcontent.summary
    link = '<span class="continue"> <a href="%s">[Continua]</a></span>' % postcontent.get_absolute_url()
    match = last_close.search(summary)
    if match:
        match = match.group(1)
        summary = summary[:-len(match)] + link + summary[-len(match):]
    else:
        summary += link
    return summary

