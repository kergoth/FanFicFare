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
    return MusicMastersAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class MusicMastersAdapter(BaseSiteAdapter):
    rrurl = 'https://www.royalroad.com/fiction/18729/music-masters'

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId', '1234')

        # normalized story URL.https://musicmastersdotblog.wordpress.com/the-discography-so-far/
        self._setURL('https://' + self.getSiteDomain() + '/the-discography-so-far/')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev', 'musicmasters')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"
        print(url)

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'musicmastersdotblog.wordpress.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://musicmastersdotblog.wordpress.com/the-discography-so-far/"

    def getSiteURLPattern(self):
        return r"https?://musicmastersdotblog\.wordpress\.com/(.*)$"

    ## Getting the chapter list and the meta data, plus 'is adult' checking.
    def doExtractChapterUrlsAndMetadata(self, get_cover=True):
        url = self.url
        logger.debug("URL: "+url)

        try:
            data = self._fetchUrl(url)
        except HTTPError as e:
            if e.code == 404:
                raise exceptions.StoryDoesNotExist(self.url)
            else:
                raise e

        # Pull the description and cover image from the Royal Road version
        rrsoup = self.make_soup(self._fetchUrl(self.rrurl))
        description = rrsoup.find('div', {'class': 'description'})
        if description:
            self.setDescription(url, description.get_text())

        if get_cover:
            rrheader = rrsoup.find('div', {'class': 'fic-header'})
            if rrheader:
                cover = rrheader.find('img')
                if cover:
                    self.setCoverImage(url, cover['src'])

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        ## Title
        title = soup.find('meta', {'name': 'application-name'})
        if title:
            self.story.setMetadata('title', title['content'])

        # Find authorid and URL from... author url.
        author = 'Hejin57'
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', 'http://'+self.host+'/')
        self.story.setMetadata('author', author)

        # toc list of links is everything inside the first div.entry-content we find
        toc = soup.find('div', {'class': 'entry-content'})

        # Remove Share link garbage
        toc.find(attrs={'id': 'jp-post-flair'}).decompose()

        datepattern = re.compile(r"/20\d\d/\d\d/\d\d/")
        current_track = None
        for element in toc.find_all(['h2', 'a']):
            if element.name == 'h2':
                current_track = unicode(element.string)
                continue

            href = element['href']
            if datepattern.search(href) is None:
                element['href'] = unicode(self._fetchUrlOpened(href)[1].geturl())
            self.add_chapter(current_track + ' ' + unicode(element.string), element['href'])

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div', {'class': 'entry-content'})

        # Remove Share link garbage
        div.find(attrs={'id': 'jp-post-flair'}).decompose()

        for link in div.find_all('a'):
            link.decompose()

        if div is None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, div)
