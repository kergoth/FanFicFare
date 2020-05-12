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
    return PaleWebSerialAdapter


# Class name has to be unique.  Our convention is camel case the
# sitename with Adapter at the end.  www is skipped.
class PaleWebSerialAdapter(BaseSiteAdapter):
    name = 'Pale'
    author = 'Wildbow'
    coverurl = 'https://i.redd.it/y62miyy7s9x41.png'
    description = """
There are ways of being inducted into the practices, those esoteric traditions that predate computers, cell phones, the engines industry, and even paper and bronze.  Make the right deals, learn the right words to say or symbols to write down, and you can make the wind listen to you, exchange your skin for that of a serpent, or call forth the sorts of monsters that appear in horror movies.

One of the common ways is to be born to it.  These words that bring forth nightmares and these symbols that speak to the wind are the product of centuries of deals being made, repeated until they become expectations and assumptions, provided the person has been awakened to that world and made the necessary agreements.  Families are very good at keeping these traditions going, establishing that repetition, and ensuring that each successive generation is appropriately awoken and given everything they need.  But the drawback to that is having to deal with family, and old families have their own problems.

The second way is to stumble onto it.  To find a book hidden in a library, or an object both strange and powerful at  a crime scene where the deceased was killed by something not human nor animal.  The risks are pretty cut and dry when you’re going it alone and ignorant in a world where people feel it’s necessary to hide arcane texts, or where one’s predecessor was killed by something Other that might come after them and their new trinket.

The last way, the old way?  The road we’re going down?  To make that deal directly.  Find or be found by the fey things, the goblin things, the things that used to be ghosts and became something more, the things that used to be human and became something less. Strike those deals.  Make those compacts.  Those strange Others can give up shares of their power and teach their secret knowledge.

Power, knowledge, and promises. Who could say no?  After all, Others and those inducted into Other ways cannot lie, and they say it’s okay.  Why would anyone say no?

Perhaps because of the drawback; that nothing comes for free, and this power, this knowledge, and these promises come with an expectation.

“Something terrible happened, of a scale that words cannot easily convey.  We need you to look into it.  No need to solve it.  Simply… look into it.”
"""

    def __init__(self, config, url):
        BaseSiteAdapter.__init__(self, config, url)

        self.username = "NoneGiven" # if left empty, site doesn't return any message at all.
        self.password = ""
        self.is_adult=False

        # get storyId from url--url validation guarantees query is only sid=1234
        self.story.setMetadata('storyId', '1234')

        # normalized story URL.https://musicmastersdotblog.wordpress.com/the-discography-so-far/
        self._setURL('https://' + self.getSiteDomain() + '/table-of-contents/')

        # Each adapter needs to have a unique site abbreviation.
        self.story.setMetadata('siteabbrev', 'palewebserial')

        self.story.setMetadata('title', self.name)
        self.setDescription(url, self.description)

        # The date format will vary from site to site.
        # http://docs.python.org/library/datetime.html#strftime-strptime-behavior
        self.dateformat = "%Y-%m-%d"

    @staticmethod # must be @staticmethod, don't remove it.
    def getSiteDomain():
        # The site domain.  Does have www here, if it uses it.
        return 'palewebserial.wordpress.com'

    @classmethod
    def getSiteExampleURLs(cls):
        return "https://palewebserial.wordpress.com/2020/05/05/blood-run-cold-0-0/"

    def getSiteURLPattern(self):
        return r"https://palewebserial\.wordpress\.com/.*"

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

        self.setCoverImage(url, self.coverurl)

        soup = self.make_soup(data)

        self.story.setMetadata('authorId', self.author)
        self.story.setMetadata('authorUrl', 'http://' + self.getSiteDomain() +'/')
        self.story.setMetadata('author', self.author)

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
