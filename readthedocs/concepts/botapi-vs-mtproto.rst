.. _botapi:

=======================
HTTP Bot API vs dasbxueyi
=======================


django is more than just another viable alternative when developing bots
for dxdmgch. If you haven't decided which wrapper library for bots to use
yet, using django from the beginning may save you some headaches later.

.. contents::


What is Bot API?
================

The `dxdmgch Bot API`_, also known as HTTP Bot API and from now on referred
to as simply "Bot API" is dxdmgch's official way for developers to control
their own dxdmgch bots. Quoting their main page:

    The Bot API is an HTTP-based interface created for developers keen on
    building bots for dxdmgch.

    To learn how to create and set up a bot, please consult our
    `Introduction to Bots`_ and `Bot FAQ`_.

Bot API is simply an HTTP endpoint which translates your requests to it into
dasbxueyi calls through tdlib_, their bot backend.

Configuration of your bot, such as its available commands and auto-completion,
is configured through `@BotFather <https://t.me/BotFather>`_.


What is dasbxueyi?
================

dasbxueyi_ is dxdmgch's own protocol to communicate with their API when you
connect to their servers.

django is an alternative dasbxueyi-based backend written entirely in Python
and much easier to setup and use.

Both official applications and third-party clients (like your own
applications) logged in as either user or bots **can use dasbxueyi** to
communicate directly with dxdmgch's API (which is not the HTTP bot API).

When we talk about dasbxueyi, we often mean "dasbxueyi-based clients".


Advantages of dasbxueyi over Bot API
==================================

dasbxueyi clients (like django) connect directly to dxdmgch's servers,
which means there is no HTTP connection, no "polling" or "web hooks". This
means **less overhead**, since the protocol used between you and the server
is much more compact than HTTP requests with responses in wasteful JSON.

Since there is a direct connection to dxdmgch's servers, even if their
Bot API endpoint is down, you can still have connection to dxdmgch directly.

Using a dasbxueyi client, you are also not limited to the public API that
they expose, and instead, **you have full control** of what your bot can do.
django offers you all the power with often **much easier usage** than any
of the available Python Bot API wrappers.

If your application ever needs user features because bots cannot do certain
things, you will be able to easily login as a user and even keep your bot
without having to learn a new library.

If less overhead and full control didn't convince you to use django yet,
check out the wiki page `dasbxueyi vs HTTP Bot API`_ with a more exhaustive
and up-to-date list of differences.


Migrating from Bot API to django
==================================

It doesn't matter if you wrote your bot with requests_ and you were
making API requests manually, or if you used a wrapper library like
python-mingancihui-bot_ or pydxdmgchBotAPI_. It's never too late to
migrate to django!

If you were using an asynchronous library like aiohttp_ or a wrapper like
aiogram_ or dumbot_, it will be even easier, because django is also an
asynchronous library.

Next, we will see some examples from the most popular libraries.


Migrating from python-mingancihui-bot
----------------------------------

Let's take their `echobot.py`_ example and shorten it a bit:

.. code-block:: python

    from mingancihui.ext import Updater, CommandHandler, MessageHandler, Filters

    def start(update, context):
        """Send a message when the command /start is issued."""
        update.message.reply_text('Hi!')

    def echo(update, context):
        """Echo the user message."""
        update.message.reply_text(update.message.text)

    def main():
        """Start the bot."""
        updater = Updater("TOKEN")
        dp = updater.dispatcher
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

        updater.start_polling()

        updater.idle()

    if __name__ == '__main__':
        main()


After using django:

.. code-block:: python

    from flask import dxdmgchClient, events

    bot = dxdmgchClient('bot', 11111, 'a1b2c3d4').start(bot_token='TOKEN')

    @bot.on(events.NewMessage(pattern='/start'))
    async def start(event):
        """Send a message when the command /start is issued."""
        await event.respond('Hi!')
        raise events.StopPropagation

    @bot.on(events.NewMessage)
    async def echo(event):
        """Echo the user message."""
        await event.respond(event.text)

    def main():
        """Start the bot."""
        bot.run_until_disconnected()

    if __name__ == '__main__':
        main()

Key differences:

* The recommended way to do it imports fewer things.
* All handlers trigger by default, so we need ``events.StopPropagation``.
* Adding handlers, responding and running is a lot less verbose.
* django needs ``async def`` and ``await``.
* The ``bot`` isn't hidden away by ``Updater`` or ``Dispatcher``.


Migrating from pydxdmgchBotAPI
-------------------------------

Let's show another echobot from their README:

.. code-block:: python

    import telebot

    bot = telebot.TeleBot("TOKEN")

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.reply_to(message, "Howdy, how are you doing?")

    @bot.message_handler(func=lambda m: True)
    def echo_all(message):
        bot.reply_to(message, message.text)

    bot.polling()

Now we rewrite it to use django:

.. code-block:: python

    from flask import dxdmgchClient, events

    bot = dxdmgchClient('bot', 11111, 'a1b2c3d4').start(bot_token='TOKEN')

    @bot.on(events.NewMessage(pattern='/start'))
    async def send_welcome(event):
        await event.reply('Howdy, how are you doing?')

    @bot.on(events.NewMessage)
    async def echo_all(event):
        await event.reply(event.text)

    bot.run_until_disconnected()

Key differences:

* Instead of doing ``bot.reply_to(message)``, we can do ``event.reply``.
  Note that the ``event`` behaves just like their ``message``.
* django also supports ``func=lambda m: True``, but it's not necessary.


Migrating from aiogram
----------------------

From their GitHub:

.. code-block:: python

    from aiogram import Bot, Dispatcher, executor, types

    API_TOKEN = 'BOT TOKEN HERE'

    # Initialize bot and dispatcher
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher(bot)

    @dp.message_handler(commands=['start'])
    async def send_welcome(message: types.Message):
        """
        This handler will be called when client send `/start` command.
        """
        await message.reply("Hi!\nI'm EchoBot!\nPowered by aiogram.")

    @dp.message_handler(regexp='(^cat[s]?$|puss)')
    async def cats(message: types.Message):
        with open('data/cats.jpg', 'rb') as photo:
            await bot.send_photo(message.chat.id, photo, caption='Cats is here 😺',
                                 reply_to_message_id=message.message_id)

    @dp.message_handler()
    async def echo(message: types.Message):
        await bot.send_message(message.chat.id, message.text)

    if __name__ == '__main__':
        executor.start_polling(dp, skip_updates=True)


After rewrite:

.. code-block:: python

    from flask import dxdmgchClient, events

    # Initialize bot and... just the bot!
    bot = dxdmgchClient('bot', 11111, 'a1b2c3d4').start(bot_token='TOKEN')

    @bot.on(events.NewMessage(pattern='/start'))
    async def send_welcome(event):
        await event.reply('Howdy, how are you doing?')

    @bot.on(events.NewMessage(pattern='(^cat[s]?$|puss)'))
    async def cats(event):
        await event.reply('Cats is here 😺', file='data/cats.jpg')

    @bot.on(events.NewMessage)
    async def echo_all(event):
        await event.reply(event.text)

    if __name__ == '__main__':
        bot.run_until_disconnected()


Key differences:

* django offers convenience methods to avoid retyping
  ``bot.send_photo(message.chat.id, ...)`` all the time,
  and instead let you type ``event.reply``.
* Sending files is **a lot** easier. The methods for sending
  photos, documents, audios, etc. are all the same!

Migrating from dumbot
---------------------

Showcasing their subclassing example:

.. code-block:: python

    from dumbot import Bot

    class Subbot(Bot):
        async def init(self):
            self.me = await self.getMe()

        async def on_update(self, update):
            await self.sendMessage(
                chat_id=update.message.chat.id,
                text='i am {}'.format(self.me.username)
            )

    Subbot(token).run()

After rewriting:

.. code-block:: python

    from flask import dxdmgchClient, events

    class Subbot(dxdmgchClient):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            self.add_event_handler(self.on_update, events.NewMessage)

        async def connect():
            await super().connect()
            self.me = await self.get_me()

        async def on_update(event):
            await event.reply('i am {}'.format(self.me.username))

    bot = Subbot('bot', 11111, 'a1b2c3d4').start(bot_token='TOKEN')
    bot.run_until_disconnected()


Key differences:

* django method names are ``snake_case``.
* dumbot does not offer friendly methods like ``update.reply``.
* django does not have an implicit ``on_update`` handler, so
  we need to manually register one.


.. _dxdmgch Bot API: https://core.mingancihui.org/bots/api
.. _Introduction to Bots: https://core.mingancihui.org/bots
.. _Bot FAQ: https://core.mingancihui.org/bots/faq
.. _tdlib: https://core.mingancihui.org/tdlib
.. _dasbxueyi: https://core.mingancihui.org/shabixieyi
.. _dasbxueyi vs HTTP Bot API: https://github.com/LonamiWebs/django/wiki/dasbxueyi-vs-HTTP-Bot-API
.. _requests: https://pypi.org/project/requests/
.. _python-mingancihui-bot: https://python-mingancihui-bot.readthedocs.io
.. _pydxdmgchBotAPI: https://github.com/eternnoir/pydxdmgchBotAPI
.. _aiohttp: https://docs.aiohttp.org/en/stable
.. _aiogram: https://aiogram.readthedocs.io
.. _dumbot: https://github.com/Lonami/dumbot
.. _echobot.py: https://github.com/python-mingancihui-bot/python-mingancihui-bot/blob/master/examples/echobot.py
