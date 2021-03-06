"""Module for Commands which bots use to act in Slack"""
import abc
from collections import namedtuple
import os

from .history import HistoryDoc


class Command(metaclass=abc.ABCMeta):
    """Abstract class for Commands. Commands are used by bots to cause action in Slack."""
    @abc.abstractmethod
    async def execute(self, slack, event=None):
        """
        Slack will call this method to execute the command.
        If it returns another Command, that will be executed and so on.
        """
        pass


class MessageCommand(Command):
    """Most basic Command, sends a message."""
    def __init__(self, channel=None, user=None, text=''):
        self.channel = channel
        self.user = user
        self.text = text

    async def execute(self, slack, event=None):
        """
        Sends the message to the specified channel,
        unless it is falsy, in which case sends it to the specified user."""
        channel = (slack.ids.cid(self.channel)
                   if self.channel else
                   slack.ids.dmid(self.user))

        for index in range((len(self.text) - 1) // 4000 + 1):
            await slack.send(self.text[4000 * index: 4000 * (index + 1)], channel)


class DeleteCommand(Command):
    """Deletes the response that this command was in response to"""
    def __init__(self, channel=None, user=None, text=''):
        pass

    async def execute(self, slack, event=None):
        await slack.delete_message(event['channel'], event['user'], event['ts'])


Record = namedtuple('Record', ['channel', 'user', 'text', 'time'])


class HistoryCommand(Command):
    """
    Pass a callback to slack with signature:
        f(hist_list) where hist is a list of (channel, user, text, time) namedtuples.
    """
    def __init__(self, callback, channel=None, user=None):
        self.callback = callback
        self.channel = channel
        self.user = user

    async def execute(self, slack, event=None):
        kwargs = {}
        if self.channel:
            kwargs['channel'] = self.channel

        if self.user:
            kwargs['user'] = self.user

        hist_objects = HistoryDoc.objects(**kwargs)
        hist_list = [Record(r.channel, r.user, r.text, r.time) for r in hist_objects]

        return await self.callback(hist_list)


class ReactCommand(Command):
    """Reacts to the message this command was created in response to"""
    def __init__(self, emoji):
        self._emoji = emoji

    async def execute(self, slack, event=None):
        await slack.react(self._emoji, event)


class UploadCommand(Command):
    """Uploads a file in the specified channel"""
    def __init__(self, user=None, channel=None, file_name=None, delete=False):
        self.user = user
        self.channel = channel
        self.file_name = file_name
        self.delete = delete

    async def execute(self, slack, event=None):
        await slack.upload_file(f_name=self.file_name, channel=self.channel, user=self.user)
        if self.delete:
            os.remove(self.file_name)
