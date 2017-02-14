import base64
from .util import encode_bugzilla_datetime

class BugzillaObject(dict):
    # Treat the object-attributes as dict-indizes for easier jsoning
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delitem__ = dict.__delitem__
    
    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, dict.__repr__(self.to_json()))
    
    # convert the object to a jsonable-version to send as request
    # if id_only is true, return only the most important attributes
    # (e.g. to avoid recursion)
    # things like converting dates to bugzilla-representation or attachment-data
    # to base64 should happen here
    def to_json(self, id_only = False):
        raise RuntimeError("Subclasses have to implement this method")

class Attachment(BugzillaObject):
    ATTRIBUTES = {
        "data":             b"",
        "creation_time":    None,
        "last_change_time": None,
        "id":               -1,
        "bug_id":           -1,
        "file_name":        "",
        "summary":          "",
        "content_type":     "",
        "is_private":       False,
        "is_obsolete":      False,
        "is_patch":         False,
        "creator":          None,
        "flags":            []
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        for key, value in Attachment.ATTRIBUTES.items():
            self.setdefault(key, value)
    
    def __getattr__(self, attr):
        # to avoid the trouble of setting the size along with the data, size is
        # a virtual attribute
        if attr == "size":
            return len(self.data)
        else:
            return BugzillaObject.__getattr__(self, attr)
    
    def to_json(self):
        obj = dict(self)
        obj["size"] = self.size
        obj["data"] = base64.b64encode(self.data).decode("ascii")
        obj["creation_time"] = encode_bugzilla_datetime(self.creation_time)
        obj["last_change_time"] = encode_bugzilla_datetime(self.last_change_time)
        obj["flags"] = [flag.to_json() for flag in self.flags]
        
        return obj

class Flag(BugzillaObject):
    ATTRIBUTES = {
        "id":                -1,
        "name":              "",
        "type_id":           -1,
        "creation_date":     None,
        "modification_date": None,
        "status":            "",
        "setter":            None,
        "requestee":         None
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        for key, value in Flag.ATTRIBUTES.items():
            self.setdefault(key, value)
    
    def to_json(self):
        obj = dict(self)
        obj["creation_date"] = encode_bugzilla_datetime(self.creation_date)
        obj["modification_date"] = encode_bugzilla_datetime(self.modification_date)
        
        return obj
