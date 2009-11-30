# -*- coding: UTF-8 -*-
from __future__ import absolute_import

import re
from random import randint
from django import template
from django.db.models import Count
from django.conf import settings as dsettings
from django.contrib import comments
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.template.defaultfilters import slugify
from django.template.loader import render_to_string
from django.utils.translation import ugettext

from microblog import models, settings
from tagging.models import Tag

register = template.Library()

class LastBlogPost(template.Node):
    def __init__(self, limit, var_name):
        self.var_name = var_name
        self.limit = limit

    def render(self, context):
        lang = context.get('LANGUAGE_CODE', settings.MICROBLOG_DEFAULT_LANGUAGE)
        contents = models.PostContent.objects.published(language = lang).select_related()
        if self.limit:
            contents = contents[:self.limit]
        posts = [ (c.post, c) for c in contents ]
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
def year_list(parser, token):
    """
    {% year_list ["include-empty"] as var_name %}
    """
    class Years(template.Node):
        def __init__(self, include_empty, var_name):
            self.include_empty = bool(include_empty)
            self.var_name = var_name
        def render(self, context):
            # questo funziona solo con sqlite
            sql = """
            SELECT strftime('%%%%Y', date) as d, count(*)
            FROM microblog_post
            %s
            GROUP BY strftime('%%%%Y', date)
            ORDER BY d DESC;
            """
            if context['user'].is_anonymous():
                sql = sql % "WHERE microblog_post.status = 'P'"
            else:
                sql = sql % ''

            from django.db import connection, transaction
            cursor = connection.cursor()

            cursor.execute(sql)
            rows = cursor.fetchall()
            context[self.var_name] = rows
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
    return Years(empty, var_name)

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
            c = models.Category.objects\
                .all()\
                .order_by('name')
            if context['user'].is_anonymous():
                # se l'utente non è registrato mostro solo i post pubblicabili,
                # quelli, cioè, che non sono in draft e hanno una traduzione
                # nella lingua corrente.

                # purtroppo non riesco ad esprimere con una sola query
                # (modificando c) il filtro sui post pubblicabili senza
                # ripetere qui il codice presente nel PostManager.
                # Al momento ho optato per una doppia query, se le prestazioni
                # dovessero risentirne possiamo utilizzare uan cache o fare un
                # po' di refactorin.
                posts = models.Post.objects.published(lang = context['LANGUAGE_CODE'])
                c = models.Category.objects.filter(post__in = list(posts))

            c = c.annotate(count = Count('post'))
            if not self.include_empty:
                c = c.filter(count__gt = 0)
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

@register.tag
def author_list(parser, token):
    """
    {% author_list as var_name %}
    """
    class Authors(template.Node):
        def __init__(self, var_name):
            self.var_name = var_name

        def render(self, context):
            authors = set([ p.author for p in models.Post.objects.published() ])
            context[self.var_name] = authors
            return ''

    contents = token.split_contents()
    tag_name = contents.pop(0)
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    return Authors(var_name)

@register.tag
def tags_list(parser, token):
    """
    {% tags_list as var_name %}
    """
    class Tags(template.Node):
        def __init__(self, var_name):
            self.var_name = var_name

        def render(self, context):
            # 2009-10-16: questo per funzionare ha bisogno di una patch a tagging
            tags = Tag.objects.usage_for_queryset(
                models.Post.objects.published(lang = context['LANGUAGE_CODE']),
                counts = True)
            context[self.var_name] = tags
            return ''

    contents = token.split_contents()
    tag_name = contents.pop(0)
    if contents[-2] != 'as':
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % tag_name)
    var_name = contents[-1]
    return Tags(var_name)

def _show_post_summary(context, post):
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
            content = None
    context.update({
        'post': post,
        'content': content,
    })
    return context

@register.inclusion_tag('microblog/show_post_entry.html', takes_context=True)
def show_post_entry(context, post):
    return _show_post_summary(context, post)

@register.inclusion_tag('microblog/show_post_summary.html', takes_context=True)
def show_post_summary(context, post):
    return _show_post_summary(context, post)

@register.inclusion_tag('microblog/show_post_detail.html', takes_context=True)
def show_post_detail(context, content, options=None):
    if context['user'].is_anonymous() and not content.post.is_published():
        return {}
    context.update({
        'post': content.post,
        'options': options,
        'content': content,
    })
    return context

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
    continue_string = ugettext("Continua")
    link = '<span class="continue"> <a href="%s">%s&nbsp;&rarr;</a></span>' % (postcontent.get_absolute_url(), continue_string)
    match = last_close.search(summary)
    if match:
        match = match.group(1)
        summary = summary[:-len(match)] + link + summary[-len(match):]
    else:
        summary += link
    return summary

@register.filter
def user_name_for_url(user):
    """
    """
    return slugify('%s-%s' % (user.first_name, user.last_name))

@register.tag
def get_post_comment_count(parser, token):
    """
    {% get_post_comment_count post as var_name %}
    """
    class CommentsCount(template.Node):
        def __init__(self, object, var_name):
            self.object = template.Variable(object)
            self.var_name = var_name
            self.comment_model = comments.get_model()

        def render(self, context):
            o = self.object.resolve(context)
            ctype = ContentType.objects.get_for_model(o)
            qs = self.comment_model.objects.filter(
                content_type = ctype,
                object_pk = o.id,
                is_public = True,
            ).count()
            context[self.var_name] = qs
            return ''

    contents = token.split_contents()
    try:
        tag_name, arg, _, var_name = contents
    except ValueError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % contents[0])
    return CommentsCount(arg, var_name)

@register.tag
def get_post_comment(parser, token):
    """
    {% get_post_comment post as var_name %}
    """
    class Comments(template.Node):
        def __init__(self, object, var_name):
            self.object = template.Variable(object)
            self.var_name = var_name
            self.comment_model = comments.get_model()

        def render(self, context):
            o = self.object.resolve(context)
            ctype = ContentType.objects.get_for_model(o)
            qs = self.comment_model.objects.filter(
                content_type = ctype,
                object_pk = o.id,
            )
            context[self.var_name] = qs
            return ''

    contents = token.split_contents()
    try:
        tag_name, arg, _, var_name = contents
    except ValueError:
        raise template.TemplateSyntaxError("%r tag had invalid arguments" % contents[0])
    return Comments(arg, var_name)

@register.inclusion_tag('microblog/show_post_comments.html', takes_context = True)
def show_post_comments(context, post):
    context.update({
        'post': post,
    })
    return context

@register.filter
def post_published(q, lang):
    """
    Filtra i post passati lasciando solo quelli pubblicabili.
    """
    # TODO: al momento q può essere solo un queryset, bisognerebbe prevedere il
    # caso in cui q sia un iterable di post
    return models.Post.objects.published(q = q, lang = lang)
