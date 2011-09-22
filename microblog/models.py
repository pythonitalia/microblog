# -*- coding: UTF-8 -*-
from django.conf import settings as dsettings
from django.contrib.auth.models import User
from django.core import mail
from django.db import models
from django.db.models.signals import post_save
from django.template import Template, Context
from django.utils.importlib import import_module

from taggit.managers import TaggableManager

from microblog import settings
from microblog.django_urls import UrlMixin

import logging

log = logging.getLogger('microblog')

class Category(models.Model):
    name = models.CharField(max_length = 100)
    description = models.TextField(blank = True)

    class Meta:
        verbose_name_plural = 'Categories'

    def __unicode__(self):
        return self.name

POST_STATUS = (('P', 'Pubblicato'), ('D', 'Bozza'))

class PostManager(models.Manager):
    def all(self, lang = None):
        q = super(PostManager, self).all()
        if lang:
            q = self.filterPostsByLanguage(q, lang)
        return q

    def published(self, lang=None, q=None, user=None):
        if q is None:
            q = self.all()
        if lang:
            q = self.filterPostsByLanguage(q, lang)
        if user is None or user.is_anonymous():
            q = q.filter(status='P')
        elif not user.is_superuser:
            q = q.filter(models.Q(author=user) | models.Q(status='P'))
        return q

    def filterPostsByLanguage(self, query, lang):
        return query\
            .filter(postcontent__language = lang)\
            .exclude(postcontent__headline='')

    def filterPostsByFeaturedStatus(self, query, featured):
        return query.filter(featured=featured)

    def featured(self):
        return self.filterPostsByFeaturedStatus(self.published(), featured=True)

class Post(models.Model, UrlMixin):
    date = models.DateTimeField(db_index=True)
    author = models.ForeignKey(User)
    status = models.CharField(max_length = 1, default = 'D', choices = POST_STATUS)
    allow_comments = models.BooleanField()
    category = models.ForeignKey(Category)
    featured = models.BooleanField(default=False)
    image = models.URLField(verify_exists=False, null=True, blank=True)

    tags = TaggableManager()

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

    def spammed(self, method, value):
        return self.spam_set.filter(method=method, value=value).count() > 0

SPAM_METHODS = (
    ('e', 'email'),
    ('t', 'twitter'),
)
class Spam(models.Model):
    """
    tiene traccia di dove, come e quando un determinato post è stato
    pubblicizzato.
    """
    post = models.ForeignKey(Post)
    method = models.CharField(max_length=1, choices=SPAM_METHODS)
    value = models.CharField(max_length=100)
    date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s -> %s' % (self.method, self.value)

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

    _twitter_template = Template(settings.MICROBLOG_TWITTER_MESSAGE_TEMPLATE)
    def post_update_on_twitter(sender, instance, created, **kwargs):
        if settings.MICROBLOG_TWITTER_LANGUAGES is not None and instance.language not in settings.MICROBLOG_TWITTER_LANGUAGES:
            return
        post = instance.post
        if not post.is_published():
            return

        try:
            if not isinstance(settings.MICROBLOG_TWITTER_POST_URL_MANGLER, str):
                url = settings.MICROBLOG_TWITTER_POST_URL_MANGLER(instance)
            else:
                module, attr = settings.MICROBLOG_TWITTER_POST_URL_MANGLER.rsplit('.', 1)
                mod = import_module(module)
                url = getattr(mod, attr)(instance)
        except Exception, e:
            message = 'Post: "%s"\n\nCannot retrieve the url: "%s"' % (instance.headline, str(e))
            mail.mail_admins('[blog] error preparing the tweet', message)
            return

        existent = set(( x.value for x in Spam.objects.filter(post=post, method='t') ))
        recipients = set((settings.MICROBLOG_TWITTER_USERNAME,)) - existent
        if not recipients:
            return

        context = Context({
            'content': instance,
            'headline': instance.headline,
            'url': url,
        })
        status = _twitter_template.render(context)
        diff_len = len(status) - 140
        if diff_len > 0:
            context = Context({
                'content': instance,
                'headline': truncate_headline(instance.headline, diff_len),
                'url': url,
            })
            status = _twitter_template.render(context)
        if settings.MICROBLOG_TWITTER_DEBUG:
            print 'Tweet for', instance.headline.encode('utf-8')
            print status
            print '--------------------------------------------'
            return
        log.info('"%s" tweet on "%s"', instance.headline.encode('utf-8'), settings.MICROBLOG_TWITTER_USERNAME)
        try:
            api = twitter.Api(settings.MICROBLOG_TWITTER_USERNAME, settings.MICROBLOG_TWITTER_PASSWORD)
            api.PostUpdate(status)
            s = Spam(post=post, method='t', value=settings.MICROBLOG_TWITTER_USERNAME)
            s.save()
        except Exception, e:
            message = 'Post: "%s"\n\nCannot post status update: "%s"' % (instance.headline, str(e))
            mail.mail_admins('[blog] error tweeting the new status', message)
            return

    post_save.connect(post_update_on_twitter, sender=PostContent)

if settings.MICROBLOG_EMAIL_INTEGRATION:
    _email_templates = {
        'subject': Template(settings.MICROBLOG_EMAIL_SUBJECT_TEMPLATE),
        'body': Template(settings.MICROBLOG_EMAIL_BODY_TEMPLATE),
    }
    def post_update_on_email(sender, instance, created, **kwargs):
        if settings.MICROBLOG_EMAIL_LANGUAGES is not None and instance.language not in settings.MICROBLOG_EMAIL_LANGUAGES:
            return
        post = instance.post
        if not post.is_published():
            return

        existent = set(( x.value for x in Spam.objects.filter(post=post, method='e') ))
        recipients = set(settings.MICROBLOG_EMAIL_RECIPIENTS) - existent
        if not recipients:
            return

        ctx = Context({
            'content': instance,
        })
        from django.utils.html import strip_tags
        from lxml import html
        from lxml.html.clean import clean_html

        subject = strip_tags(_email_templates['subject'].render(ctx))
        try:
            hdoc = html.fromstring(_email_templates['body'].render(ctx))
        except Exception, e:
            message = 'Post: "%s"\n\nCannot parse as html: "%s"' % (subject, str(e))
            mail.mail_admins('[blog] error while sending mail', message)
            return
        # dalla doc di lxml:
        # The module lxml.html.clean provides a Cleaner class for cleaning up
        # HTML pages. It supports removing embedded or script content, special
        # tags, CSS style annotations and much more.  Say, you have an evil web
        # page from an untrusted source that contains lots of content that
        # upsets browsers and tries to run evil code on the client side:
        #
        # Noi non dobbiamo proteggerci da codice maligno, ma vista la
        # situazione dei client email, possiamo rimuovere embed, javascript,
        # iframe.; tutte cose che non vengono quasi mai renderizzate per bene
        hdoc = clean_html(hdoc)

        # rendo tutti i link assoluti, in questo modo funzionano anche in un
        # client di posta
        hdoc.make_links_absolute(dsettings.DEFAULT_URL_PREFIX)

        body_html = html.tostring(hdoc)

        # per i client di posta che non supportano l'html ecco una versione in
        # solo test
        import html2text
        body_text = html2text.html2text(body_html)

        for r in recipients:
            log.info('"%s" email to "%s"', instance.headline.encode('utf-8'), r)
            email = mail.EmailMultiAlternatives(subject, body_text, dsettings.DEFAULT_FROM_EMAIL, [r])
            email.attach_alternative(body_html, 'text/html')
            email.send()
            s = Spam(post=post, method='e', value=r)
            s.save()
    post_save.connect(post_update_on_email, sender=PostContent)

import moderation
