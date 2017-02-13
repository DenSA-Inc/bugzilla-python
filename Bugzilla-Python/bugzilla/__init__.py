import json
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError
import base64
from datetime import datetime

# the constants and functions below refer to
# https://bugzilla.readthedocs.io/en/5.0/api/core/v1/general.html#common-data-types
BUGZILLA_DATE_FORMAT = "%Y-%m-%d"
BUGZILLA_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

def parse_bugzilla_datetime(string):
    return datetime.strptime(string, BUGZILLA_DATETIME_FORMAT)

def parse_bugzilla_date(string):
    return datetime.strptime(string, BUGZILLA_DATE_FORMAT)

def encode_bugzilla_datetime(dt):
    if dt is None:
        return None
    
    return dt.strftime(BUGZILLA_DATETIME_FORMAT)

def encode_bugzilla_date(dt):
    if dt is None:
        return None
    
    return dt.strftime(BUGZILLA_DATE_FORMAT)

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

class BugzillaException(Exception):
    def __init__(self, code, *args, **kw):
        Exception.__init__(self, *args, **kw)
        self.error_code = code
    
    def __str__(self):
        return "Error code %i: %s" % (self.error_code, Exception.__str__(self))
    
    def get_error_code(self):
        return self.error_code

class Bugzilla:
    def __init__(self, url, api_key = None):
        if not url.endswith("/"):
            raise ValueError("Url has to end with /")
        if not url.endswith("rest/"):
            url += "rest/"
        
        self.url = url
        self.api_key = None
        self.charset = "utf-8" # i have to lookup the right charset, until then utf-8 should suffice
    
    def _get(self, path, **kw):
        if self.api_key:
            kw["api_key"] = self.api_key
        # sequences supplied for the in/exclude_fields will automatically be comma-joined
        if not isinstance(kw.get("include_fields", ""), str):
            kw["include_fields"] = ",".join(kw["include_fields"])
        if not isinstance(kw.get("exclude_fields", ""), str):
            kw["exclude_fields"] = ",".join(kw["exclude_fields"])
        
        query = urlencode(kw)
        if query: query = "?" + query
        url = self.url + path + query
        try:
            data = urlopen(url).read()
            obj = json.loads(data.decode(self.charset))
        except HTTPError as e:
            # some api-errors set the http-status, so here we might still get
            # a valid json-object that will result in a bugzilla-error
            data = e.fp.read()
            try:
                obj = json.loads(data.decode(self.charset))
            except ValueError:
                # no valid api-response, maybe a http-500 or something else
                raise e
        
        if obj.get("error"):
            raise BugzillaException(obj["code"], obj["message"])
        
        return obj
    
    def get_attachment(self, attachment_id, **kw):
        'https://bugzilla.readthedocs.io/en/5.0/api/core/v1/attachment.html'
        attachment_id = str(attachment_id)
        return self._get_attachment(self._get("bug/attachment/" + attachment_id, **kw)["attachments"][attachment_id])
    
    def get_attachments_by_bug(self, bug_id, **kw):
        'https://bugzilla.readthedocs.io/en/5.0/api/core/v1/attachment.html'
        bug_id = str(bug_id)
        return [self._get_attachment(data) for data in self._get("bug/%s/attachment" % bug_id, **kw)["bugs"][bug_id]]
    
    def _get_attachment(self, data):
        if "creation_time" in data: data["creation_time"] = parse_bugzilla_datetime(data["creation_time"])
        if "last_change_time" in data: data["last_change_time"] = parse_bugzilla_datetime(data["last_change_time"])
        if "data" in data: data["data"] = base64.b64decode(data["data"])
        if "size" in data: del data["size"]
        if "is_private" in data: data["is_private"] = bool(data["is_private"])
        if "is_obsolete" in data: data["is_obsolete"] = bool(data["is_obsolete"])
        if "is_patch" in data: data["is_patch"] = bool(data["is_patch"])
        
        return Attachment(data)
