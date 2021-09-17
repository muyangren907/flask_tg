import datetime
import io
import os
import pathlib
import typing
import inspect
import asyncio

from .._crypto import AES
from .._misc import utils, helpers, requestiter, tlobject
from .. import errors, hints, _tl

try:
    import aiohttp
except ImportError:
    aiohttp = None

if typing.TYPE_CHECKING:
    from .telegramclient import TelegramClient

# Chunk sizes for upload.getFile must be multiples of the smallest size
MIN_CHUNK_SIZE = 4096
MAX_CHUNK_SIZE = 512 * 1024

# 2021-01-15, users reported that `errors.TimeoutError` can occur while downloading files.
TIMED_OUT_SLEEP = 1

class _DirectDownloadIter(requestiter.RequestIter):
    async def _init(
            self, file, dc_id, offset, stride, chunk_size, request_size, file_size, msg_data
    ):
        self.request = _tl.fn.upload.GetFile(
            file, offset=offset, limit=request_size)

        self.total = file_size
        self._stride = stride
        self._chunk_size = chunk_size
        self._last_part = None
        self._msg_data = msg_data
        self._timed_out = False

        self._exported = dc_id and self.client.session.dc_id != dc_id
        if not self._exported:
            # The used sender will also change if ``FileMigrateError`` occurs
            self._sender = self.client._sender
        else:
            try:
                self._sender = await self.client._borrow_exported_sender(dc_id)
            except errors.DcIdInvalidError:
                # Can't export a sender for the ID we are currently in
                config = await self.client(_tl.fn.help.GetConfig())
                for option in config.dc_options:
                    if option.ip_address == self.client.session.server_address:
                        self.client.session.set_dc(
                            option.id, option.ip_address, option.port)
                        self.client.session.save()
                        break

                # TODO Figure out why the session may have the wrong DC ID
                self._sender = self.client._sender
                self._exported = False

    async def _load_next_chunk(self):
        cur = await self._request()
        self.buffer.append(cur)
        if len(cur) < self.request.limit:
            self.left = len(self.buffer)
            await self.close()
        else:
            self.request.offset += self._stride

    async def _request(self):
        try:
            result = await self.client._call(self._sender, self.request)
            self._timed_out = False
            if isinstance(result, _tl.upload.FileCdnRedirect):
                raise NotImplementedError  # TODO Implement
            else:
                return result.bytes

        except errors.TimeoutError as e:
            if self._timed_out:
                self.client._log[__name__].warning('Got two timeouts in a row while downloading file')
                raise

            self._timed_out = True
            self.client._log[__name__].info('Got timeout while downloading file, retrying once')
            await asyncio.sleep(TIMED_OUT_SLEEP)
            return await self._request()

        except errors.FileMigrateError as e:
            self.client._log[__name__].info('File lives in another DC')
            self._sender = await self.client._borrow_exported_sender(e.new_dc)
            self._exported = True
            return await self._request()

        except errors.FilerefUpgradeNeededError as e:
            # Only implemented for documents which are the ones that may take that long to download
            if not self._msg_data \
                    or not isinstance(self.request.location, _tl.InputDocumentFileLocation) \
                    or self.request.location.thumb_size != '':
                raise

            self.client._log[__name__].info('File ref expired during download; refetching message')
            chat, msg_id = self._msg_data
            msg = await self.client.get_messages(chat, ids=msg_id)

            if not isinstance(msg.media, _tl.MessageMediaDocument):
                raise

            document = msg.media.document

            # Message media may have been edited for something else
            if document.id != self.request.location.id:
                raise

            self.request.location.file_reference = document.file_reference
            return await self._request()

    async def close(self):
        if not self._sender:
            return

        try:
            if self._exported:
                await self.client._return_exported_sender(self._sender)
            elif self._sender != self.client._sender:
                await self._sender.disconnect()
        finally:
            self._sender = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()


class _GenericDownloadIter(_DirectDownloadIter):
    async def _load_next_chunk(self):
        # 1. Fetch enough for one chunk
        data = b''

        # 1.1. ``bad`` is how much into the data we have we need to offset
        bad = self.request.offset % self.request.limit
        before = self.request.offset

        # 1.2. We have to fetch from a valid offset, so remove that bad part
        self.request.offset -= bad

        done = False
        while not done and len(data) - bad < self._chunk_size:
            cur = await self._request()
            self.request.offset += self.request.limit

            data += cur
            done = len(cur) < self.request.limit

        # 1.3 Restore our last desired offset
        self.request.offset = before

        # 2. Fill the buffer with the data we have
        # 2.1. Slicing `bytes` is expensive, yield `memoryview` instead
        mem = memoryview(data)

        # 2.2. The current chunk starts at ``bad`` offset into the data,
        #      and each new chunk is ``stride`` bytes apart of the other
        for i in range(bad, len(data), self._stride):
            self.buffer.append(mem[i:i + self._chunk_size])

            # 2.3. We will yield this offset, so move to the next one
            self.request.offset += self._stride

        # 2.4. If we are in the last chunk, we will return the last partial data
        if done:
            self.left = len(self.buffer)
            await self.close()
            return

        # 2.5. If we are not done, we can't return incomplete chunks.
        if len(self.buffer[-1]) != self._chunk_size:
            self._last_part = self.buffer.pop().tobytes()

            # 3. Be careful with the offsets. Re-fetching a bit of data
            #    is fine, since it greatly simplifies things.
            # TODO Try to not re-fetch data
            self.request.offset -= self._stride


async def download_profile_photo(
        self: 'TelegramClient',
        entity: 'hints.EntityLike',
        file: 'hints.FileLike' = None,
        *,
        download_big: bool = True) -> typing.Optional[str]:
    # hex(crc32(x.encode('ascii'))) for x in
    # ('User', 'Chat', 'UserFull', 'ChatFull')
    ENTITIES = (0x2da17977, 0xc5af5d94, 0x1f4661b9, 0xd49a2697)
    # ('InputPeer', 'InputUser', 'InputChannel')
    INPUTS = (0xc91c90b6, 0xe669bf46, 0x40f202fd)
    if not isinstance(entity, tlobject.TLObject) or entity.SUBCLASS_OF_ID in INPUTS:
        entity = await self.get_entity(entity)

    thumb = -1 if download_big else 0

    possible_names = []
    if entity.SUBCLASS_OF_ID not in ENTITIES:
        photo = entity
    else:
        if not hasattr(entity, 'photo'):
            # Special case: may be a ChatFull with photo:Photo
            # This is different from a normal UserProfilePhoto and Chat
            if not hasattr(entity, 'chat_photo'):
                return None

            return await _download_photo(
                self, entity.chat_photo, file, date=None,
                thumb=thumb, progress_callback=None
            )

        for attr in ('username', 'first_name', 'title'):
            possible_names.append(getattr(entity, attr, None))

        photo = entity.photo

    if isinstance(photo, (_tl.UserProfilePhoto, _tl.ChatPhoto)):
        dc_id = photo.dc_id
        loc = _tl.InputPeerPhotoFileLocation(
            peer=await self.get_input_entity(entity),
            photo_id=photo.photo_id,
            big=download_big
        )
    else:
        # It doesn't make any sense to check if `photo` can be used
        # as input location, because then this method would be able
        # to "download the profile photo of a message", i.e. its
        # media which should be done with `download_media` instead.
        return None

    file = _get_proper_filename(
        file, 'profile_photo', '.jpg',
        possible_names=possible_names
    )

    try:
        result = await self.download_file(loc, file, dc_id=dc_id)
        return result if file is bytes else file
    except errors.LocationInvalidError:
        # See issue #500, Android app fails as of v4.6.0 (1155).
        # The fix seems to be using the full channel chat photo.
        ie = await self.get_input_entity(entity)
        ty = helpers._entity_type(ie)
        if ty == helpers._EntityType.CHANNEL:
            full = await self(_tl.fn.channels.GetFullChannel(ie))
            return await _download_photo(
                self, full.full_chat.chat_photo, file,
                date=None, progress_callback=None,
                thumb=thumb
            )
        else:
            # Until there's a report for chats, no need to.
            return None

async def download_media(
        self: 'TelegramClient',
        message: 'hints.MessageLike',
        file: 'hints.FileLike' = None,
        *,
        thumb: 'typing.Union[int, _tl.TypePhotoSize]' = None,
        progress_callback: 'hints.ProgressCallback' = None) -> typing.Optional[typing.Union[str, bytes]]:
    # Downloading large documents may be slow enough to require a new file reference
    # to be obtained mid-download. Store (input chat, message id) so that the message
    # can be re-fetched.
    msg_data = None

    # TODO This won't work for messageService
    if isinstance(message, _tl.Message):
        date = message.date
        media = message.media
        msg_data = (message.input_chat, message.id) if message.input_chat else None
    else:
        date = datetime.datetime.now()
        media = message

    if isinstance(media, str):
        media = utils.resolve_bot_file_id(media)

    if isinstance(media, _tl.MessageService):
        if isinstance(message.action,
                        _tl.MessageActionChatEditPhoto):
            media = media.photo

    if isinstance(media, _tl.MessageMediaWebPage):
        if isinstance(media.webpage, _tl.WebPage):
            media = media.webpage.document or media.webpage.photo

    if isinstance(media, (_tl.MessageMediaPhoto, _tl.Photo)):
        return await _download_photo(
            self, media, file, date, thumb, progress_callback
        )
    elif isinstance(media, (_tl.MessageMediaDocument, _tl.Document)):
        return await _download_document(
            self, media, file, date, thumb, progress_callback, msg_data
        )
    elif isinstance(media, _tl.MessageMediaContact) and thumb is None:
        return _download_contact(
            self, media, file
        )
    elif isinstance(media, (_tl.WebDocument, _tl.WebDocumentNoProxy)) and thumb is None:
        return await _download_web_document(
            self, media, file, progress_callback
        )

async def download_file(
        self: 'TelegramClient',
        input_location: 'hints.FileLike',
        file: 'hints.OutFileLike' = None,
        *,
        part_size_kb: float = None,
        file_size: int = None,
        progress_callback: 'hints.ProgressCallback' = None,
        dc_id: int = None,
        key: bytes = None,
        iv: bytes = None) -> typing.Optional[bytes]:
    return await _download_file(
        self,
        input_location,
        file,
        part_size_kb=part_size_kb,
        file_size=file_size,
        progress_callback=progress_callback,
        dc_id=dc_id,
        key=key,
        iv=iv,
    )

async def _download_file(
        self: 'TelegramClient',
        input_location: 'hints.FileLike',
        file: 'hints.OutFileLike' = None,
        *,
        part_size_kb: float = None,
        file_size: int = None,
        progress_callback: 'hints.ProgressCallback' = None,
        dc_id: int = None,
        key: bytes = None,
        iv: bytes = None,
        msg_data: tuple = None) -> typing.Optional[bytes]:
    if not part_size_kb:
        if not file_size:
            part_size_kb = 64  # Reasonable default
        else:
            part_size_kb = utils.get_appropriated_part_size(file_size)

    part_size = int(part_size_kb * 1024)
    if part_size % MIN_CHUNK_SIZE != 0:
        raise ValueError(
            'The part size must be evenly divisible by 4096.')

    if isinstance(file, pathlib.Path):
        file = str(file.absolute())

    in_memory = file is None or file is bytes
    if in_memory:
        f = io.BytesIO()
    elif isinstance(file, str):
        # Ensure that we'll be able to download the media
        helpers.ensure_parent_dir_exists(file)
        f = open(file, 'wb')
    else:
        f = file

    try:
        async for chunk in _iter_download(
                self, input_location, request_size=part_size, dc_id=dc_id, msg_data=msg_data):
            if iv and key:
                chunk = AES.decrypt_ige(chunk, key, iv)
            r = f.write(chunk)
            if inspect.isawaitable(r):
                await r

            if progress_callback:
                r = progress_callback(f.tell(), file_size)
                if inspect.isawaitable(r):
                    await r

        # Not all IO objects have flush (see #1227)
        if callable(getattr(f, 'flush', None)):
            f.flush()

        if in_memory:
            return f.getvalue()
    finally:
        if isinstance(file, str) or in_memory:
            f.close()

def iter_download(
        self: 'TelegramClient',
        file: 'hints.FileLike',
        *,
        offset: int = 0,
        stride: int = None,
        limit: int = None,
        chunk_size: int = None,
        request_size: int = MAX_CHUNK_SIZE,
        file_size: int = None,
        dc_id: int = None
):
    return _iter_download(
        self,
        file,
        offset=offset,
        stride=stride,
        limit=limit,
        chunk_size=chunk_size,
        request_size=request_size,
        file_size=file_size,
        dc_id=dc_id,
    )

def _iter_download(
        self: 'TelegramClient',
        file: 'hints.FileLike',
        *,
        offset: int = 0,
        stride: int = None,
        limit: int = None,
        chunk_size: int = None,
        request_size: int = MAX_CHUNK_SIZE,
        file_size: int = None,
        dc_id: int = None,
        msg_data: tuple = None
):
    info = utils._get_file_info(file)
    if info.dc_id is not None:
        dc_id = info.dc_id

    if file_size is None:
        file_size = info.size

    file = info.location

    if chunk_size is None:
        chunk_size = request_size

    if limit is None and file_size is not None:
        limit = (file_size + chunk_size - 1) // chunk_size

    if stride is None:
        stride = chunk_size
    elif stride < chunk_size:
        raise ValueError('stride must be >= chunk_size')

    request_size -= request_size % MIN_CHUNK_SIZE
    if request_size < MIN_CHUNK_SIZE:
        request_size = MIN_CHUNK_SIZE
    elif request_size > MAX_CHUNK_SIZE:
        request_size = MAX_CHUNK_SIZE

    if chunk_size == request_size \
            and offset % MIN_CHUNK_SIZE == 0 \
            and stride % MIN_CHUNK_SIZE == 0 \
            and (limit is None or offset % limit == 0):
        cls = _DirectDownloadIter
        self._log[__name__].info('Starting direct file download in chunks of '
                                    '%d at %d, stride %d', request_size, offset, stride)
    else:
        cls = _GenericDownloadIter
        self._log[__name__].info('Starting indirect file download in chunks of '
                                    '%d at %d, stride %d', request_size, offset, stride)

    return cls(
        self,
        limit,
        file=file,
        dc_id=dc_id,
        offset=offset,
        stride=stride,
        chunk_size=chunk_size,
        request_size=request_size,
        file_size=file_size,
        msg_data=msg_data,
    )


def _get_thumb(thumbs, thumb):
    # Seems Telegram has changed the order and put `PhotoStrippedSize`
    # last while this is the smallest (layer 116). Ensure we have the
    # sizes sorted correctly with a custom function.
    def sort_thumbs(thumb):
        if isinstance(thumb, _tl.PhotoStrippedSize):
            return 1, len(thumb.bytes)
        if isinstance(thumb, _tl.PhotoCachedSize):
            return 1, len(thumb.bytes)
        if isinstance(thumb, _tl.PhotoSize):
            return 1, thumb.size
        if isinstance(thumb, _tl.PhotoSizeProgressive):
            return 1, max(thumb.sizes)
        if isinstance(thumb, _tl.VideoSize):
            return 2, thumb.size

        # Empty size or invalid should go last
        return 0, 0

    thumbs = list(sorted(thumbs, key=sort_thumbs))

    for i in reversed(range(len(thumbs))):
        # :tl:`PhotoPathSize` is used for animated stickers preview, and the thumb is actually
        # a SVG path of the outline. Users expect thumbnails to be JPEG files, so pretend this
        # thumb size doesn't actually exist (#1655).
        if isinstance(thumbs[i], _tl.PhotoPathSize):
            thumbs.pop(i)

    if thumb is None:
        return thumbs[-1]
    elif isinstance(thumb, int):
        return thumbs[thumb]
    elif isinstance(thumb, str):
        return next((t for t in thumbs if t.type == thumb), None)
    elif isinstance(thumb, (_tl.PhotoSize, _tl.PhotoCachedSize,
                            _tl.PhotoStrippedSize, _tl.VideoSize)):
        return thumb
    else:
        return None

def _download_cached_photo_size(self: 'TelegramClient', size, file):
    # No need to download anything, simply write the bytes
    if isinstance(size, _tl.PhotoStrippedSize):
        data = utils.stripped_photo_to_jpg(size.bytes)
    else:
        data = size.bytes

    if file is bytes:
        return data
    elif isinstance(file, str):
        helpers.ensure_parent_dir_exists(file)
        f = open(file, 'wb')
    else:
        f = file

    try:
        f.write(data)
    finally:
        if isinstance(file, str):
            f.close()
    return file

async def _download_photo(self: 'TelegramClient', photo, file, date, thumb, progress_callback):
    """Specialized version of .download_media() for photos"""
    # Determine the photo and its largest size
    if isinstance(photo, _tl.MessageMediaPhoto):
        photo = photo.photo
    if not isinstance(photo, _tl.Photo):
        return

    # Include video sizes here (but they may be None so provide an empty list)
    size = _get_thumb(photo.sizes + (photo.video_sizes or []), thumb)
    if not size or isinstance(size, _tl.PhotoSizeEmpty):
        return

    if isinstance(size, _tl.VideoSize):
        file = _get_proper_filename(file, 'video', '.mp4', date=date)
    else:
        file = _get_proper_filename(file, 'photo', '.jpg', date=date)

    if isinstance(size, (_tl.PhotoCachedSize, _tl.PhotoStrippedSize)):
        return _download_cached_photo_size(self, size, file)

    if isinstance(size, _tl.PhotoSizeProgressive):
        file_size = max(size.sizes)
    else:
        file_size = size.size

    result = await self.download_file(
        _tl.InputPhotoFileLocation(
            id=photo.id,
            access_hash=photo.access_hash,
            file_reference=photo.file_reference,
            thumb_size=size.type
        ),
        file,
        file_size=file_size,
        progress_callback=progress_callback
    )
    return result if file is bytes else file

def _get_kind_and_names(attributes):
    """Gets kind and possible names for :tl:`DocumentAttribute`."""
    kind = 'document'
    possible_names = []
    for attr in attributes:
        if isinstance(attr, _tl.DocumentAttributeFilename):
            possible_names.insert(0, attr.file_name)

        elif isinstance(attr, _tl.DocumentAttributeAudio):
            kind = 'audio'
            if attr.performer and attr.title:
                possible_names.append('{} - {}'.format(
                    attr.performer, attr.title
                ))
            elif attr.performer:
                possible_names.append(attr.performer)
            elif attr.title:
                possible_names.append(attr.title)
            elif attr.voice:
                kind = 'voice'

    return kind, possible_names

async def _download_document(
        self, document, file, date, thumb, progress_callback, msg_data):
    """Specialized version of .download_media() for documents."""
    if isinstance(document, _tl.MessageMediaDocument):
        document = document.document
    if not isinstance(document, _tl.Document):
        return

    if thumb is None:
        kind, possible_names = _get_kind_and_names(document.attributes)
        file = _get_proper_filename(
            file, kind, utils.get_extension(document),
            date=date, possible_names=possible_names
        )
        size = None
    else:
        file = _get_proper_filename(file, 'photo', '.jpg', date=date)
        size = _get_thumb(document.thumbs, thumb)
        if isinstance(size, (_tl.PhotoCachedSize, _tl.PhotoStrippedSize)):
            return _download_cached_photo_size(self, size, file)

    result = await _download_file(
        _tl.InputDocumentFileLocation(
            id=document.id,
            access_hash=document.access_hash,
            file_reference=document.file_reference,
            thumb_size=size.type if size else ''
        ),
        file,
        file_size=size.size if size else document.size,
        progress_callback=progress_callback,
        msg_data=msg_data,
    )

    return result if file is bytes else file

def _download_contact(cls, mm_contact, file):
    """
    Specialized version of .download_media() for contacts.
    Will make use of the vCard 4.0 format.
    """
    first_name = mm_contact.first_name
    last_name = mm_contact.last_name
    phone_number = mm_contact.phone_number

    # Remove these pesky characters
    first_name = first_name.replace(';', '')
    last_name = (last_name or '').replace(';', '')
    result = (
        'BEGIN:VCARD\n'
        'VERSION:4.0\n'
        'N:{f};{l};;;\n'
        'FN:{f} {l}\n'
        'TEL;TYPE=cell;VALUE=uri:tel:+{p}\n'
        'END:VCARD\n'
    ).format(f=first_name, l=last_name, p=phone_number).encode('utf-8')

    if file is bytes:
        return result
    elif isinstance(file, str):
        file = cls._get_proper_filename(
            file, 'contact', '.vcard',
            possible_names=[first_name, phone_number, last_name]
        )
        f = open(file, 'wb')
    else:
        f = file

    try:
        f.write(result)
    finally:
        # Only close the stream if we opened it
        if isinstance(file, str):
            f.close()

    return file

async def _download_web_document(cls, web, file, progress_callback):
    """
    Specialized version of .download_media() for web documents.
    """
    if not aiohttp:
        raise ValueError(
            'Cannot download web documents without the aiohttp '
            'dependency install it (pip install aiohttp)'
        )

    # TODO Better way to get opened handles of files and auto-close
    in_memory = file is bytes
    if in_memory:
        f = io.BytesIO()
    elif isinstance(file, str):
        kind, possible_names = cls._get_kind_and_names(web.attributes)
        file = cls._get_proper_filename(
            file, kind, utils.get_extension(web),
            possible_names=possible_names
        )
        f = open(file, 'wb')
    else:
        f = file

    try:
        with aiohttp.ClientSession() as session:
            # TODO Use progress_callback; get content length from response
            # https://github.com/telegramdesktop/tdesktop/blob/c7e773dd9aeba94e2be48c032edc9a78bb50234e/Telegram/SourceFiles/ui/images.cpp#L1318-L1319
            async with session.get(web.url) as response:
                while True:
                    chunk = await response.content.read(128 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
    finally:
        if isinstance(file, str) or file is bytes:
            f.close()

    return f.getvalue() if in_memory else file

def _get_proper_filename(file, kind, extension,
                            date=None, possible_names=None):
    """Gets a proper filename for 'file', if this is a path.

        'kind' should be the kind of the output file (photo, document...)
        'extension' should be the extension to be added to the file if
                    the filename doesn't have any yet
        'date' should be when this file was originally sent, if known
        'possible_names' should be an ordered list of possible names

        If no modification is made to the path, any existing file
        will be overwritten.
        If any modification is made to the path, this method will
        ensure that no existing file will be overwritten.
    """
    if isinstance(file, pathlib.Path):
        file = str(file.absolute())

    if file is not None and not isinstance(file, str):
        # Probably a stream-like object, we cannot set a filename here
        return file

    if file is None:
        file = ''
    elif os.path.isfile(file):
        # Make no modifications to valid existing paths
        return file

    if os.path.isdir(file) or not file:
        try:
            name = None if possible_names is None else next(
                x for x in possible_names if x
            )
        except StopIteration:
            name = None

        if not name:
            if not date:
                date = datetime.datetime.now()
            name = '{}_{}-{:02}-{:02}_{:02}-{:02}-{:02}'.format(
                kind,
                date.year, date.month, date.day,
                date.hour, date.minute, date.second,
            )
        file = os.path.join(file, name)

    directory, name = os.path.split(file)
    name, ext = os.path.splitext(name)
    if not ext:
        ext = extension

    result = os.path.join(directory, name + ext)
    if not os.path.isfile(result):
        return result

    i = 1
    while True:
        result = os.path.join(directory, '{} ({}){}'.format(name, i, ext))
        if not os.path.isfile(result):
            return result
        i += 1