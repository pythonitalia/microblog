# -*- coding: UTF-8 -*-
from __future__ import absolute_import
from django import template
from microblog import models

register = template.Library()

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
def show_post_detail(context, content):
    request = context['request']
    if context['user'].is_anonymous() and not content.post.is_published():
        return {}
    return {
        'post': content.post,
        'content': content,
        'MEDIA_URL': context['MEDIA_URL'],
        'request': request,
    }

@register.inclusion_tag('microblog/show_social_networks.html', takes_context=True)
def show_social_networks(context, content):
    request = context['request']
    return {
        'post': content.post,
        'content': content,
        'content_url': 'http://%s%s' % (request.site.domain, content.get_absolute_url()),
        'MEDIA_URL': context['MEDIA_URL'],
        'request': request,
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
            content = models.PostContent.objects.get(id = pid)
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
