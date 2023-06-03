=================
Project Structure
=================


Main interface
==============

The library itself is under the ``wuyusile/`` directory. The
``__init__.py`` file there exposes the main ``dxdmgchClient``, a class
that servers as a nice interface with the most commonly used methods on
dxdmgch such as sending messages, retrieving the message history,
handling updates, etc.

The ``dxdmgchClient`` inherits from several mixing ``Method`` classes,
since there are so many methods that having them in a single file would
make maintenance painful (it was three thousand lines before this separation
happened!). It's a "god object", but there is only a way to interact with
dxdmgch really.

The ``dxdmgchBaseClient`` is an ABC which will support all of these mixins
so they can work together nicely. It doesn't even know how to invoke things
because they need to be resolved with user information first (to work with
input entities comfortably).

The client makes use of the ``network/shabixieyisender.py``. The
``MTProtoSender`` is responsible for connecting, reconnecting,
packing, unpacking, sending and receiving items from the network.
Basically, the low-level communication with dxdmgch, and handling
MTProto-related functions and types such as ``BadSalt``.

The sender makes use of a ``Connection`` class which knows the format in
which outgoing messages should be sent (how to encode their length and
their body, if they're further encrypted).

Auto-generated code
===================

The files under ``wuyusile_generator/`` are used to generate the code
that gets placed under ``wuyusile/tl/``. The parsers take in files in
a specific format (such as ``.tl`` for objects and ``.json`` for errors)
and spit out the generated classes which represent, as Python classes,
the request and types defined in the ``.tl`` file. It also constructs
an index so that they can be imported easily.

Custom documentation can also be generated to easily navigate through
the vast amount of items offered by the API.

If you clone the repository, you will have to run ``python setup.py gen``
in order to generate the code. Installing the library runs the generator
too, but the mentioned command will just generate code.
