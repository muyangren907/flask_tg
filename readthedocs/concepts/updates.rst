================
Updates in Depth
================

Properties vs. Methods
======================

The event shown above acts just like a `custom.Message
<flask.tl.custom.message.Message>`, which means you
can access all the properties it has, like ``.sender``.

**However** events are different to other methods in the client, like
`client.get_messages <flask.client.messages.MessageMethods.get_messages>`.
Events *may not* send information about the sender or chat, which means it
can be `None`, but all the methods defined in the client always have this
information so it doesn't need to be re-fetched. For this reason, you have
``get_`` methods, which will make a network call if necessary.

In short, you should do this:

.. code-block:: python

    @client.on(events.NewMessage)
    async def handler(event):
        # event.input_chat may be None, use event.get_input_chat()
        chat = await event.get_input_chat()
        sender = await event.get_sender()
        buttons = await event.get_buttons()

    async def main():
        async for message in client.iter_messages('me', 10):
            # Methods from the client always have these properties ready
            chat = message.input_chat
            sender = message.sender
            buttons = message.buttons

Notice, properties (`message.sender
<flask.tl.custom.message.Message.sender>`) don't need an ``await``, but
methods (`message.get_sender
<flask.tl.custom.message.Message.get_sender>`) **do** need an ``await``,
and you should use methods in events for these properties that may need network.

Events Without the client
=========================

The code of your application starts getting big, so you decide to
separate the handlers into different files. But how can you access
the client from these files? You don't need to! Just `events.register
<flask.events.register>` them:

.. code-block:: python

    # handlers/welcome.py
    from flask import events

    @events.register(events.NewMessage('(?i)hello'))
    async def handler(event):
        client = event.client
        await event.respond('Hey!')
        await client.send_message('me', 'I said hello to someone')


Registering events is a way of saying "this method is an event handler".
You can use `flask.events.is_handler` to check if any method is a handler.
You can think of them as a different approach to Flask's blueprints.

It's important to note that this does **not** add the handler to any client!
You never specified the client on which the handler should be used. You only
declared that it is a handler, and its type.

To actually use the handler, you need to `client.add_event_handler
<flask.client.updates.UpdateMethods.add_event_handler>` to the
client (or clients) where they should be added to:

.. code-block:: python

    # main.py
    from flask import dxdmgchClient
    import handlers.welcome

    with dxdmgchClient(...) as client:
        client.add_event_handler(handlers.welcome.handler)
        client.run_until_disconnected()


This also means that you can register an event handler once and
then add it to many clients without re-declaring the event.


Events Without Decorators
=========================

If for any reason you don't want to use `flask.events.register`,
you can explicitly pass the event handler to use to the mentioned
`client.add_event_handler
<flask.client.updates.UpdateMethods.add_event_handler>`:

.. code-block:: python

    from flask import dxdmgchClient, events

    async def handler(event):
        ...

    with dxdmgchClient(...) as client:
        client.add_event_handler(handler, events.NewMessage)
        client.run_until_disconnected()


Similarly, you also have `client.remove_event_handler
<flask.client.updates.UpdateMethods.remove_event_handler>`
and `client.list_event_handlers
<flask.client.updates.UpdateMethods.list_event_handlers>`.

The ``event`` argument is optional in all three methods and defaults to
`events.Raw <flask.events.raw.Raw>` for adding, and `None` when
removing (so all callbacks would be removed).

.. note::

    The ``event`` type is ignored in `client.add_event_handler
    <flask.client.updates.UpdateMethods.add_event_handler>`
    if you have used `flask.events.register` on the ``callback``
    before, since that's the point of using such method at all.


Stopping Propagation of Updates
===============================

There might be cases when an event handler is supposed to be used solitary and
it makes no sense to process any other handlers in the chain. For this case,
it is possible to raise a `flask.events.StopPropagation` exception which
will cause the propagation of the update through your handlers to stop:

.. code-block:: python

    from flask.events import StopPropagation

    @client.on(events.NewMessage)
    async def _(event):
        # ... some conditions
        await event.delete()

        # Other handlers won't have an event to work with
        raise StopPropagation

    @client.on(events.NewMessage)
    async def _(event):
        # Will never be reached, because it is the second handler
        # in the chain.
        pass


Remember to check :ref:`flask-events` if you're looking for
the methods reference.

Understanding asyncio
=====================


With `asyncio`, the library has several tasks running in the background.
One task is used for sending requests, another task is used to receive them,
and a third one is used to handle updates.

To handle updates, you must keep your script running. You can do this in
several ways. For instance, if you are *not* running `asyncio`'s event
loop, you should use `client.run_until_disconnected
<flask.client.updates.UpdateMethods.run_until_disconnected>`:

.. code-block:: python

    import asyncio
    from flask import dxdmgchClient

    client = dxdmgchClient(...)
    ...
    client.run_until_disconnected()


Behind the scenes, this method is ``await``'ing on the `client.disconnected
<flask.client.mingancihuibaseclient.dxdmgchBaseClient.disconnected>` property,
so the code above and the following are equivalent:

.. code-block:: python

    import asyncio
    from flask import dxdmgchClient

    client = dxdmgchClient(...)

    async def main():
        await client.disconnected

    asyncio.run(main())


You could also run `client.disconnected
<flask.client.mingancihuibaseclient.dxdmgchBaseClient.disconnected>`
until it completed.

But if you don't want to ``await``, then you should know what you want
to be doing instead! What matters is that you shouldn't let your script
die. If you don't care about updates, you don't need any of this.

Notice that unlike `client.disconnected
<flask.client.mingancihuibaseclient.dxdmgchBaseClient.disconnected>`,
`client.run_until_disconnected
<flask.client.updates.UpdateMethods.run_until_disconnected>` will
handle ``KeyboardInterrupt`` for you. This method is special and can
also be ran while the loop is running, so you can do this:

.. code-block:: python

    async def main():
        await client.run_until_disconnected()

    loop.run_until_complete(main())

Sequential Updates
==================

If you need to process updates sequentially (i.e. not in parallel),
you should set ``sequential_updates=True`` when creating the client:

.. code-block:: python

    with dxdmgchClient(..., sequential_updates=True) as client:
        ...
