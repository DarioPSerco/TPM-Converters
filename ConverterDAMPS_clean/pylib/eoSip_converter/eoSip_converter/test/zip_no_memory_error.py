import zipfile
import zlib


def explode(out, zip, name):
    """
    Given a 'zip' instance, copy data from the 'name' to the
    'out' stream.
    """
    zinfo = zip.getinfo(name)

    if zinfo.compress_type == zipfile.ZIP_STORED:
        decoder = None
    elif zinfo.compress_type == zipfile.ZIP_DEFLATED:
        decoder = zlib.decompressobj(-zlib.MAX_WBITS)
    else:
        raise zipfile.BadZipFile("unsupported compression method")

    zip.fp.seek(zinfo.file_offset)

    size = zinfo.compress_size

    while 1:
        data = zip.fp.read(min(size, 8192))
        if not data:
            break
        size -= len(data)
        if decoder:
            data = decoder.decompress(data)
            out.write(data)

    if decoder:
        out.write(decoder.decompress('Z'))
        out.write(decoder.flush())
