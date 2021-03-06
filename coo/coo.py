from pathlib import Path
import random
import asyncio

import twitter

from ._utils import zzz, tweet_template, parse_or_get
from ._exceptions import ScheduleError, TweetTypeError


class Coo:
    """
    Schedule Twitter Updates with Easy.

    Note: to use this library you need to create an account on
    https://developer.twitter.com/ and generate Keys and Access
    Tokens.

    Attributes
    ----------
    consumer : str
        Twitter consumer key.
    consumer_secret : str
        Twitter consumer secret.
    token : str
        Twitter token.
    token_secret : str
        Twitter token secret.
    preview : bool, optional
        Print the update(s) on the console (default is 'False).

    Methods
    -------
    verify()
        Verify if the authentication is valid.
    tweet(updates, _delay=None, _interval=None, template=None, time_zone="local")
        Post Twitter Updates from a list of strings.
    schedule(updates, time_zone='local')
        Post multiple Twitter Updates from a list of tuples.
    _str_update()
        Post a Twitter Update from a string.
    """

    time_zone: str = "local"
    media = None
    global_media = None
    global_template = None

    def __init__(self, consumer, consumer_secret, token, token_secret, preview=False):
        """
        Parameters
        ----------
        consumer : str
            Twitter consumer key.
        consumer_secret : str
            Twitter consumer secret.
        token : str
            Twitter token.
        token_secret : str
            Twitter token secret.
        preview : bool, optional
            Print the update(s) on the console.
        """
        # check for correct credentials types
        self._check_credentials_type(consumer, consumer_secret, token, token_secret)

        # https://github.com/bear/python-twitter
        self.consumer = consumer
        self.consumer_secret = consumer_secret
        self.token = token
        self.token_secret = token_secret

        # True to preview the update in the console.
        self.preview = preview

        # _interval and _delay switches.
        self._delay_time = True
        self._interval_time = False

        # The async loop for the custom updates.
        self.loop = asyncio.get_event_loop()

    def _check_credentials_type(self, *args):
        for credential in args:
            if not isinstance(credential, str):
                raise TypeError("Twitter credentials must be strings")

    @property
    def api(self):
        """
        Through Coo.api you gain access to all of the Python Twitter
        wrapper models:

        from coo import Coo

        >>> at = Coo("consumer", "consumer_secret", "access_token", "token_secret")
        >>> at.api.GetFollowers()

        More info: https://python-twitter.readthedocs.io/en/latest/index.html
        """
        return twitter.Api(
            self.consumer, self.consumer_secret, self.token, self.token_secret
        )

    @property
    def verify(self):
        """Verify if the authentication is valid."""
        return self.api.VerifyCredentials()

    @classmethod
    def set_time_zone(cls, time_zone):
        cls.time_zone = time_zone

    @classmethod
    def set_media_file(cls, media):
        cls.media = media

    @classmethod
    def set_global_media_file(cls, global_media):
        cls.global_media = global_media

    @classmethod
    def set_global_template(cls, global_template):
        cls.global_template = global_template

    def tweet(
        self,
        updates,
        delay=None,
        interval=None,
        template=None,
        media=media,
        time_zone=time_zone,
        aleatory=False,
    ):
        """
        Post Twitter Updates from a list of strings.

        Parameters
        ----------
        updates : list
            A list of strings, each one is a Twitter Update.
        _delay : str, int, optional
            The time before the first Update.
        _interval : str, int, optional
            The time between Updates.
        template : str, optional
            A string to serve as a template. Need to has a "$message".
        media : str, optional
            PATH to a local file, or a file-like object (something
            with a read() method).
        time_zone : str, optional
            Sets a time zone for parsing datetime strings (default is 'local'):
            https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        aleatory : bool, optional
            Tweet the updates randomly (default is 'False').

        Raises
        ------
        TweetTypeError
            When "updates" is not a list or its elements are not strings.
        """
        if not isinstance(updates, list) or not isinstance(updates[0], str):
            raise TweetTypeError(TweetTypeError.wrongListMsg)

        if aleatory:
            random.shuffle(updates)
        if time_zone is not self.time_zone:
            self.set_time_zone(time_zone)
        if media:
            self.set_media_file(Path(media))

        self._delay(delay)
        for update in updates:
            self._interval(interval)
            self._str_update(update, template)

        return updates

    def schedule(
        self, updates, time_zone=time_zone, media=media, template=global_template
    ):
        """
        Post multiple Twitter Updates from a list of tuples.

        Parameters
        ----------
        updates : list
            A list of tuples that contains:

            [("datetime", "template", "update msg")]

            e.g.

            [("2040-10-30 00:05", template, "Update msg")]

            Notes for parsing date and time strings:
            - If a time zone is not specified, it will be set to local.
            - When parsing only time information the date will default to today.
            - The time will be set to 00:00:00 if it's not specified.
            - A future date is needed, otherwise, a ScheduleError is raised.

            The template is string with a "$message".

        time_zone : str, optional
            Sets a time zone for parsing datetime strings (default is 'local'):
            https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
        media : str, optional
            PATH to a local file, or a file-like object (something
            with a read() method).
        template : str, optional
            A global template for all the tweets with a "None" value on "msg[1]".

        Raises
        ------
        ScheduleError
            When the length of a tuple updates is less or greater than 3.
        """
        if not isinstance(updates[0], tuple):
            raise ScheduleError(ScheduleError.wrongListMsg)
        if template:
            self.set_global_template(template)
        if time_zone is not self.time_zone:
            self.set_time_zone(time_zone)
        if media:
            self.set_global_media_file(Path(media))

        self.loop.run_until_complete(self._async_tasks(updates))
        self.loop.close()

    def _str_update(self, update, template):
        """
        Post a Twitter Update from a string.

        Parameters
        ----------
        update : str
            A string representing a Twitter Update.
        template : str, optional
            A string to serve as a template. Need to has a "$message".

        Returns
        -------
        twitter.Api.PostUpdate
            Post the update to Twitter.
        """
        if template:
            update = tweet_template(update=update, template=template)
        elif self.global_template:
            update = tweet_template(update=update, template=self.global_template)

        if self.preview:
            print(update)
            return

        try:
            # Try to post with a media file.
            with open(self.media, "rb") as media_file:  # type: ignore
                return self.api.PostUpdate(update, media=media_file)
        except TypeError:
            # If media is not a readable type, just post the update.
            return self.api.PostUpdate(update)

    async def _async_tasks(self, custom_msgs):
        """Prepare the asyncio tasks for the custom tweets."""
        for msg in set(custom_msgs):
            if len(msg) < 3 or len(msg) > 4:
                raise ScheduleError(ScheduleError.tupleLenError)

        await asyncio.wait(
            [self.loop.create_task(self._custom_updates(post)) for post in custom_msgs]
        )

    async def _custom_updates(self, msg):
        """
        Process custom updates: templates and updates time for every
        Twitter update.
        """
        seconds = parse_or_get(msg[0], self.time_zone)
        await asyncio.sleep(seconds)

        if len(msg) == 4 and msg[3] is not None:
            self.set_media_file(Path(msg[3]))
        elif len(msg) == 3 and self.global_media:
            self.set_media_file(Path(self.global_media))
        else:
            self.set_media_file(None)

        return self._str_update(update=msg[2], template=msg[1])

    def _delay(self, _delay):
        """_delay the Post of one or multiple tweets."""
        if _delay and self._delay_time:
            zzz(_delay, self.time_zone)

            # Set to False to avoid repetition
            self._delay_time = False

    def _interval(self, _interval):
        """Add an _interval between Twitter Updates."""
        # Avoid the first iteration
        if _interval and self._interval_time is True:
            zzz(_interval)

        # Allow from the second one
        if self._interval_time is False:
            self._interval_time = True

    def __str__(self):
        return f"Twitter User: {self.verify.name}."
