# -*- coding: utf-8 -*-

# Copyright 2011 Fanficdownloader team, 2018 FanFicFare team
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import absolute_import
import logging
logger = logging.getLogger(__name__)
import re
from ..htmlcleanup import stripHTML
from .. import exceptions as exceptions

# py2 vs py3 transition
from ..six import text_type as unicode
from ..six.moves.urllib.error import HTTPError

from .base_adapter import BaseSiteAdapter,  makeDate


def getClass():
    return RaiseSomeHellAdapter


# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class RaiseSomeHellAdapter(BaseSiteAdapter):
    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId', '1234')

        # normalized story URL.https://musicmastersdotblog.wordpress.com/the-discography-so-far/
        self._setURL('https://' + self.getSiteDomain() + '/chapters/')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev', 'raisesomehell')

        self.story.setMetadata('title', 'Raise Some Hell')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'raisesomehellnovel.wordpress.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://raisesomehellnovel.wordpress.com/2018/09/17/chapter-1/"

    def getSiteURLPattern(self):
        return r"https://raisesomehellnovel\.wordpress\.com/.*"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def extractChapterUrlsAndMetadata(self):
        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        soup = self.make_soup(data)

        author = 'Soranotsky'
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', 'http://' + self.getSiteDomain() +'/')
        self.story.setMetadata('author', author)

        # toc list of links is everything inside the first div.entry-content we find
        toc = soup.find('div', {'class': 'entry-content'})

        # Remove Share link garbage
        toc.find(attrs={'id': 'jp-post-flair'}).decompose()
        chapters = toc.find_all('a')

        # postpattern = re.compile(r"/([0-9]+)$")
        editpattern = re.compile(r"/post/[^/]*/([0-9]+)$")
        datepattern = re.compile(r"/20\d\d/\d\d/\d\d/")
        # canonicalize the URLs (use the get redirect only if necessary because it is so slow)
        for chapter in chapters:
            href = chapter['href']
            # match = postpattern.search(href)
            # if match and match.group(1):
            #     href = 'https://' + self.getSiteDomain() + '/?p=' + match.group(1)
            editmatch = editpattern.search(href)
            if editmatch is not None:
                href = 'https://' + self.getSiteDomain() + '/?p=' + editmatch.group(1) + '/'

            if datepattern.search(href) is None:
                chapter['href'] = unicode(self._fetchUrlOpened(href)[1].geturl())

        for chapter in chapters:
            self.add_chapter(chapter, chapter['href'])

        description = "A young man falls down a rabbit hole to a school where people are trained " \
                      "to summon demons in order to fight. He ends up losing his past, but makes " \
                      "friends as they try to figure out who’s trying to undermine everything..."
        self.setDescription(url, description)

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div',{'class': 'entry-content'})

        for link in div.find_all('a'):
            link.decompose()

        if div is None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, div)
