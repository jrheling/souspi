import os
import tempfile

def atomic_file_write(file_to_write, data, uid=None, gid=None):
    """ Atomically (via a tempfile) write data to file at specified path.
    
        If data is None, this creates an empty file.
        If uid/gid are specified, chown accordingly. 
        Raises OSError if file rename fails.
    """
    (tmp_fh, tmp_name) = tempfile.mkstemp(dir=os.path.dirname(os.path.realpath(file_to_write)),
                                          prefix=os.path.basename(os.path.realpath(file_to_write)))
    if data is not None:
        os.write(tmp_fh,bytes(data))
    os.close(tmp_fh)
    
    if (uid is not None) or (gid is not None):
        if uid is None:
            new_uid = -1
        else:
            new_uid = uid
        if gid is None:
            new_gid = -1
        else:
            new_gid = gid
        os.chown(tmp_name, new_uid, new_gid)
    
    try:
        os.rename(tmp_name, os.path.realpath(file_to_write))
    except OSError, e:
        os.unlink(tmp_name)
        msg = "Failed to update %s: %s" % (os.path.realpath(file_to_write), e.strerror)
        raise OSError(e)
