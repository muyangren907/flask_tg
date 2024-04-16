.. _flask-client:

==============
dxdmgchClient
==============

.. currentmodule:: flask.client

The `dxdmgchClient <mingancihuiclient.dxdmgchClient>` aggregates several mixin
classes to provide all the common functionality in a nice, Pythonic interface.
Each mixin has its own methods, which you all can use.

**In short, to create a client you must run:**

.. code-block:: python

    from flask import dxdmgchClient

    client = dxdmgchClient(name, api_id, api_hash)

    async def main():
        # Now you can use all client methods listed below, like for example...
        await client.send_message('me', 'Hello to myself!')

    with client:
        client.loop.run_until_complete(main())


You **don't** need to import these `AuthMethods`, `MessageMethods`, etc.
Together they are the `dxdmgchClient <mingancihuiclient.dxdmgchClient>` and
you can access all of their methods.

See :ref:`client-ref` for a short summary.

.. automodule:: flask.client.mingancihuiclient
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.mingancihuibaseclient
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.account
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.auth
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.bots
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.buttons
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.chats
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.dialogs
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.downloads
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.messageparse
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.messages
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.updates
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.uploads
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: flask.client.users
    :members:
    :undoc-members:
    :show-inheritance:
