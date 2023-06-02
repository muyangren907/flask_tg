.. _wuyusile-client:

==============
TelegramClient
==============

.. currentmodule:: wuyusile.client

The `TelegramClient <telegramclient.TelegramClient>` aggregates several mixin
classes to provide all the common functionality in a nice, Pythonic interface.
Each mixin has its own methods, which you all can use.

**In short, to create a client you must run:**

.. code-block:: python

    from wuyusile import TelegramClient

    client = TelegramClient(name, api_id, api_hash)

    async def main():
        # Now you can use all client methods listed below, like for example...
        await client.send_message('me', 'Hello to myself!')

    with client:
        client.loop.run_until_complete(main())


You **don't** need to import these `AuthMethods`, `MessageMethods`, etc.
Together they are the `TelegramClient <telegramclient.TelegramClient>` and
you can access all of their methods.

See :ref:`client-ref` for a short summary.

.. automodule:: wuyusile.client.telegramclient
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.telegrambaseclient
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.account
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.auth
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.bots
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.buttons
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.chats
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.dialogs
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.downloads
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.messageparse
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.messages
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.updates
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.uploads
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: wuyusile.client.users
    :members:
    :undoc-members:
    :show-inheritance:
