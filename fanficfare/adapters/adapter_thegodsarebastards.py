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
    return TheGodsAreBastardsAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class TheGodsAreBastardsAdapter(BaseSiteAdapter):

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId', '1234')


        # normalized story URL.
        self._setURL('https://' + self.getSiteDomain() + '/table-of-contents/')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev', 'tiraas')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'tiraas.net'

    @classmethod
    def getSiteExampleURLs(cls):
        return "http://tiraas.net/"

    def getSiteURLPattern(self):
        return r"https?://tiraas\.net/([^/]+/)?$"

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

        # use BeautifulSoup HTML parser to make everything easier to find.
        soup = self.make_soup(data)
        # print data

        # Now go hunting for all the meta data and the chapter list.

        ## Title
        title = soup.find('h1', {'class': "site-title"}).get_text()
        self.story.setMetadata('title',title)

        # Find authorid and URL from... author url.
        author = 'D. D. Webb'
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', 'http://'+self.host+'/')
        self.story.setMetadata('author', author)

        # toc list of links is everything inside the first div.entry-content we find
        toc = soup.find('div', {'class': 'entry-content'})

        # Remove Share link garbage
        toc.find(attrs={'id': 'jp-post-flair'}).decompose()
        chapters = toc.find_all('a')

        datepattern = re.compile(r"/20\d\d/\d\d/\d\d/")
        # canonicalize the URLs (use the get redirect only if necessary because it is so slow)
        for chapter in chapters:
            href = chapter['href']
            if datepattern.search(href) is None:
                chapter['href'] = unicode(self._fetchUrlOpened(href)[1].geturl())
            chapter['href'] = href.replace('http://', 'https://', 1).replace('/tiraas.wordpress.com/', '/tiraas.net/', 1)

        chapters = sorted(chapters, key=lambda ch: ch['href'])

        for chapter in chapters:
            self.add_chapter(chapter, chapter['href'])
        sum = """Evil is rising.  The world is rent by strife.  The gods have turned away from us.  In times past, heroes of sword and sorcery have always risen to turn back the tide of darkness…  But what will become of us all, now that swords are obsolete, sorcery is industrialized, and heroism itself is considered a relic of the past?
The times are changing…
Incorporating elements of a Western, a Victorian romance, hints of steampunk and inspiration from the early novels of H. Rider Haggard and Arthur Conan Doyle, all set in a world of classic sword and sorcery, The Gods are Bastards is a genre-blending fantasy epic.
Set in a familiar high-fantasy universe of wizards, dragons and elves, the action takes place roughly fifteen hundred years after the medieval stasis in which most high fantasy is set, during an era much like Earth’s Industrial Revolution.  Mass production of enchanted goods has revolutionized all aspects of life, energy weapons have made blades and armor all but obsolete, and the world is connected and illuminated by magical analogues of trains, telegraphs and electric lights.  With progress has come social and political upheaval: the scattered feudal kingdoms of yore have been consolidated into a now-precarious Empire, the clerics of various gods have organized themselves into a mighty Universal Church, and the first stirrings of modern education and an Enlightenment ethos have taken root in a young University.  On the other hand, dragons are nearly extinct, elves have been herded onto reservations, and the days when a person could make a living as a wandering adventurer are long since over.
It’s a new world, and the people of the Empire must learn to live in it, or fall to ancient threats they have tried to forget…
"""
        self.setDescription(url,sum)

    # grab the text for an individual chapter.
    def getChapterText(self, url):

        logger.debug('Getting chapter text from: %s' % url)

        soup = self.make_soup(self._fetchUrl(url))

        div = soup.find('div',{'class': 'entry-content'})
        # Remove Share link garbage
        div.find(attrs={'id': 'jp-post-flair'}).decompose()

        for link in div.find_all('a'):
            link.decompose()

        if div is None:
            raise exceptions.FailedToDownload("Error downloading Chapter: %s!  Missing required element!" % url)

        return self.utf8FromSoup(url, div)
