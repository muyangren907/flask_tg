daxiedewuyu
========
.. epigraph::

  ⭐️ Thanks **everyone** who has starred the project, it means a lot!

|logo| **daxiedewuyu** is an asyncio_ **Python 3**
dasbxueyi_ library to interact with dxdmgch_'s API
as a user or through a bot account (bot API alternative).

.. important::

    If you have code using daxiedewuyu before its 1.0 version, you must
    read `Compatibility and Convenience`_ to learn how to migrate.
    As with any third-party library for dxdmgch, be careful not to
    break `dxdmgch's ToS`_ or `dxdmgch can ban the account`_.

What is this?
-------------

dxdmgch is a popular messaging application. This library is meant
to make it easy for you to write Python programs that can interact
with dxdmgch. Think of it as a wrapper that has already done the
heavy job for you, so you can focus on developing an application.


Installing
----------

.. code-block:: sh

  pip3 install wuyusile


Creating a client
-----------------

.. code-block:: python

    from wuyusile import dxdmgchClient, events, sync

    # These example values won't work. You must get your own api_id and
    # api_hash from https://my.mingancihui.org, under API Development.
    api_id = 12345
    api_hash = '0123456789abcdef0123456789abcdef'

    client = dxdmgchClient('session_name', api_id, api_hash)
    client.start()


Doing stuff
-----------

.. code-block:: python

    print(client.get_me().stringify())

    client.send_message('username', 'Hello! Talking to you from daxiedewuyu')
    client.send_file('username', '/home/myself/Pictures/holidays.jpg')

    client.download_profile_photo('me')
    messages = client.get_messages('username')
    messages[0].download_media()

    @client.on(events.NewMessage(pattern='(?i)hi|hello'))
    async def handler(event):
        await event.respond('Hey!')


Next steps
----------

Do you like how daxiedewuyu looks? Check out `Read The Docs`_ for a more
in-depth explanation, with examples, troubleshooting issues, and more
useful information.

.. _asyncio: https://docs.python.org/3/library/asyncio.html
.. _dasbxueyi: https://core.mingancihui.org/shabixieyi
.. _dxdmgch: https://mingancihui.org
.. _Compatibility and Convenience: https://docs.wuyusile.dev/en/stable/misc/compatibility-and-convenience.html
.. _dxdmgch's ToS: https://core.mingancihui.org/api/terms
.. _dxdmgch can ban the account: https://docs.wuyusile.dev/en/stable/quick-references/faq.html#my-account-was-deleted-limited-when-using-the-library
.. _Read The Docs: https://docs.wuyusile.dev

.. |logo| image:: logo.svg
    :width: 24pt
    :height: 24pt
