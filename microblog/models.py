# -*- coding: UTF-8 -*-
from django.db import models
import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django_urls import UrlMixin
import tagging
import tagging.fields

class Category(models.Model):
    name = models.CharField(max_length = 100)
    description = models.TextField(blank = True)

    def __unicode__(self):
        return self.name

POST_STATUS = (('P', 'Pubblicato'), ('D', 'Bozza'))

class PostManager(models.Manager):
    def published(self):
        return self.all().filter(status = 'P').order_by('-date')

class Post(models.Model):
    date = models.DateTimeField(db_index=True)
    author = models.ForeignKey(User)
    status = models.CharField(max_length = 1, default = 'P', choices = POST_STATUS)
    allow_comments = models.BooleanField()
    tags = tagging.fields.TagField()
    categories = models.ManyToManyField(Category)

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
            c = contents[settings.LANGUAGES[0][0]]
        except KeyError:
            c = contents.values()[0]
        return c

    def get_trackback_url(self):
        date = self.date
        content = self.postcontent_set.all()[0]
        return content.get_url() + '/trackback'

class PostContentManager(models.Manager):
    def getBySlugAndDate(self, slug, year, month, day):
        return self.get(
            slug = slug,
            post__date__year = int(year),
            post__date__month = int(month),
            post__date__day = int(day),
        )

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
        date = self.post.date
        return ('microblog-post-detail', (), {
            'year': str(date.year),
            'month': str(date.month).zfill(2),
            'day': str(date.day).zfill(2),
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

