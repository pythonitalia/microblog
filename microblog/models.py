# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.db import models
from django.db.models.signals import post_save
from django.template import Template, Context

from django_urls import UrlMixin
import tagging
import tagging.fields

import settings

class Category(models.Model):
    name = models.CharField(max_length = 100)
    description = models.TextField(blank = True)

    def __unicode__(self):
        return self.name

POST_STATUS = (('P', 'Pubblicato'), ('D', 'Bozza'))

class PostManager(models.Manager):
    def all(self, lang = None):
        q = super(PostManager, self).all()
        if lang:
            q = self.filterPostsByLanguage(q, lang)
        return q

    def published(self, lang = None, q = None):
        if q is None:
            q = self\
                .filter(status = 'P')\
                .order_by('-date')
        else:
            q = q.filter(status = 'P')
        if lang:
            q = self.filterPostsByLanguage(q, lang)
        return q

    def filterPostsByLanguage(self, query, lang):
        sql = '"microblog_postcontent"."headline" != \'\''
        return query\
            .filter(postcontent__language = lang)\
            .extra(where = [sql])

    def filterPostsByFeaturedStatus(self, query, featured):
        return query.filter(featured=featured)

    def featured(self):
        return self.filterPostsByFeaturedStatus(self.published(), featured=True)

class Post(models.Model, UrlMixin):
    date = models.DateTimeField(db_index=True)
    author = models.ForeignKey(User)
    status = models.CharField(max_length = 1, default = 'P', choices = POST_STATUS)
    allow_comments = models.BooleanField()
    tags = tagging.fields.TagField()
    category = models.ForeignKey(Category)
    featured = models.BooleanField(default=False)
    image = models.ImageField(upload_to=settings.MICROBLOG_UPLOAD_TO, null=True, blank=True)

    objects = PostManager()

    def __unicode__(self):
        return "Post of %s on %s" % (self.author, self.date)

    class Meta:
        ordering = ('-date',)
        get_latest_by = 'date'

    def is_published(self):
        return self.status == 'P'

    def content(self, lang, fallback=True):
        """
        Ritorna il PostContent nella lingua specificata.
        Se il PostContent non esiste e fallback è False viene sollevata
        l'eccezione ObjectDoesNotExist. Se fallback è True viene prima
        ricercato il PostContent nella lingua di default del blog, poi in
        quella del sito, se non esiste viene ritornato il primo PostContent
        esistente, se non esiste neanche questo viene sollevata l'eccezione
        ObjectDoesNotExist.
        """
        contents = dict((c.language, c) for c in self.postcontent_set.exclude(headline=''))
        if not contents:
            raise PostContent.DoesNotExist()
        try:
            return contents[lang]
        except KeyError:
            if not fallback:
                raise PostContent.DoesNotExist()

        try:
            c = contents[settings.MICROBLOG_DEFAULT_LANGUAGE]
            c = contents[dsettings.LANGUAGES[0][0]]
        except KeyError:
            c = contents.values()[0]
        return c

    def get_trackback_url(self):
        date = self.date
        content = self.postcontent_set.all()[0]
        return content.get_url() + '/trackback'

    def get_absolute_url(self):
        """
        Non ha molto senso ritornare la url di un Post dato che l'utente
        visualizza i PostContent; ma è molto comodo (per il programmatore)
        avere avere una url che identifica un post senza dover per forza
        passare da una traduzione.
        """
        content = self.content(settings.MICROBLOG_DEFAULT_LANGUAGE)
        return content.get_absolute_url()

    get_url_path = get_absolute_url

class PostContentManager(models.Manager):
    def getBySlugAndDate(self, slug, year, month, day):
        return self.get(
            slug = slug,
            post__date__year = int(year),
            post__date__month = int(month),
            post__date__day = int(day),
        )

    def getBySlugAndCategory(self, slug, category):
        return self.get(
            slug = slug,
            post__category__name = category,
        )

    def published(self, language = None):
        q = self\
            .filter(post__status = 'P')\
            .order_by('-post__date')
        if language:
            q = q.filter(language = language)
        return q

class PostContent(models.Model, UrlMixin):
    post = models.ForeignKey(Post)
    language = models.CharField(max_length = 3)
    headline = models.CharField(max_length = 200)
    slug = models.SlugField(unique_for_date = 'post.date')
    summary = models.TextField()
    body = models.TextField()

    objects = PostContentManager()

    @models.permalink
    def get_absolute_url(self):
        if settings.MICROBLOG_URL_STYLE == 'date':
            date = self.post.date
            return ('microblog-post-detail', (), {
                'year': str(date.year),
                'month': str(date.month).zfill(2),
                'day': str(date.day).zfill(2),
                'slug': self.slug
            })
        elif settings.MICROBLOG_URL_STYLE == 'category':
            return ('microblog-post-detail', (), {
                'category': self.post.category.name,
                'slug': self.slug
            })

    get_url_path = get_absolute_url

    def new_trackback(self, url, blog_name='', title='', excerpt=''):
        tb = Trackback()
        tb.content = self
        tb.url = url
        tb.blog_name = blog_name
        tb.title = title
        tb.excerpt = excerpt
        tb.save()
        return tb

class Trackback(models.Model):
    content = models.ForeignKey(PostContent)
    type = models.CharField(max_length = 2, default = 'tb')
    date = models.DateTimeField(auto_now_add = True)
    url = models.CharField(max_length = 1000)
    blog_name = models.TextField()
    title = models.TextField()
    excerpt = models.TextField()

    class Meta:
        ordering = ['-date']

if settings.MICROBLOG_TWITTER_INTEGRATION:
    import twitter

    def truncate_headline(headline, n_char):
        last = headline[-n_char - 3]
        headline = headline[:-n_char -3]
        i = len(headline)
        while last not in " ,.;:" and i:
            i -= 1
            last = headline[i]
        if i != -1:
            headline = headline[:i]
        return headline + "..."

    _twitter_templates = {
        True: Template(settings.MICROBLOG_TWITTER_MESSAGE_TEMPLATE_NEW_POST),
        False: Template(settings.MICROBLOG_TWITTER_MESSAGE_TEMPLATE_UPDATED_POST),
    }
    def post_update_on_twitter(sender, instance, created, **kwargs):
        if instance.language != settings.MICROBLOG_TWITTER_POST_LANGUAGE:
            return
        post = instance.post
        if not post.is_published():
            return
        try:
            url = settings.MICROBLOG_TWITTER_POST_URL_MANGLER(instance)
        except:
            return
        context = Context({
            "content": instance,
            "url": url,
        })
        status = _twitter_templates[created].render(context)
        diff_len = len(status) - 140
        if diff_len > 0:
            instance.headline = truncate_headline(instance.headline, diff_len)
            context = Context({
                "content": instance,
                "url": url,
            })
            status = _twitter_templates[created].render(context)
        try:
            api = twitter.Api(settings.MICROBLOG_TWITTER_USERNAME, settings.MICROBLOG_TWITTER_PASSWORD)
            api.PostUpdate(status)
        except:
            return

    post_save.connect(post_update_on_twitter, sender=PostContent)
