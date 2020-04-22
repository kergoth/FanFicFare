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
    return CerulianScrawlingAdapter

# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class CerulianScrawlingAdapter(BaseSiteAdapter):
    descriptions = {
        'heretical-edge': """When Felicity ‘Flick’ Chambers boards the bus for the first day of her junior year in high school, the most important thing on her mind is how to make everyone else take the school newspaper as seriously as she does. As a self-styled investigative reporter, she’s spent years picking through the monotony of her small town to find those few dark spots that make for compelling articles.

And yet, that search for the most remarkable of stories ends when Flick disembarks the bus to find herself in a place far away from anything she’s ever known. She faces a door that will lead her to a world where she will be taught alongside her new peers to use their extraordinary gifts to protect the mundane world from the monsters that lurk within the shadows.

One thing gives Flick and her new classmates the ability to find and defeat these creatures. One thing separates them from the average humans who never comprehend the danger posed by these dark beasts. One thing provides the strength these select few desperately need if they are going to halt the incursion of this evil.

The Heretical Edge.""",
        'heretical-edge-2': '',
        'summus-proelium': """Cassidy Evans lives in a world of superheroes and supervillains. Born to a rich, prestigious family who genuinely and openly love and care for her, she has never truly wanted for anything. It is, in so many ways, a fairy tale life.

But Cassidy is about to learn that fairy tales come at a cost. Witnessing something horrific, something that will forever change her understanding of her own family, she must learn how to cope with that knowledge. Not to mention the new superpowers that she just picked up.

Yes, Cassidy Evans lives in a world of supervillains and superheroes. And as she becomes a part of that world, she will discover that both are closer than she thinks."""
    }

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        if 'summus-proelium' in self.parsedUrl.path:
            self.story.setMetadata('storyId', 'summus-proelium')
            self.story.setMetadata('title', 'Summus Proelium')
            self._setURL('https://' + self.getSiteDomain() + '/summus-proelium-table-of-contents/')
        elif 'heretical-edge-2' in self.parsedUrl.path:
            self.story.setMetadata('storyId', 'heretical-edge-2')
            self.story.setMetadata('title', 'Heretical Edge 2')
            self._setURL('https://' + self.getSiteDomain() + '/heretical-edge-2-table-of-contents/')
        else:
            self.story.setMetadata('storyId', 'heretical-edge')
            self.story.setMetadata('title', 'Heretical Edge')
            self._setURL('https://' + self.getSiteDomain() + '/table-of-contents/')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev', 'ceruleanscrawling')

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'ceruleanscrawling.wordpress.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://ceruleanscrawling.wordpress.com/table-of-contents/"

    def getSiteURLPattern(self):
        return re.escape("https://" + self.getSiteDomain()) + "/.*table-of-contents/"

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

        author = 'Cerulean'
        self.story.setMetadata('authorId', author)
        self.story.setMetadata('authorUrl', 'http://' + self.host +'/')
        self.story.setMetadata('author', author)

        # toc list of links is everything inside the first div.entry-content we find
        toc = soup.find('div', {'class': 'entry-content'})

        # Kill link to next book
        if self.story.getMetadata('storyId') == 'heretical-edge':
            toc.find('a', attrs={'href': 'https://ceruleanscrawling.wordpress.com/heretical-edge-2-table-of-contents/'}).decompose()

        # Remove Share link garbage
        toc.find(attrs={'id': 'jp-post-flair'}).decompose()
        chapters = toc.find_all('a')

        datepattern = re.compile(r"/20\d\d/\d\d/\d\d/")
        # canonicalize the URLs (use the get redirect only if necessary because it is so slow)
        for chapter in chapters:
            href = chapter['href']
            if datepattern.search(href) is None:
                chapter['href'] = unicode(self._fetchUrlOpened(href)[1].geturl())

        chapters = sorted(chapters, key=lambda ch: ch['href'])

        for chapter in chapters:
            self.add_chapter(chapter, chapter['href'])

        description = self.descriptions.get(self.story.getMetadata('storyId'))
        if description:
            self.setDescription(url, description)

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
