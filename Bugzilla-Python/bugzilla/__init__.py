import json
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError

class BugzillaObject(dict):
    # Treat the object-attributes as dict-indizes for easier jsoning
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delitem__ = dict.__delitem__
    
    # convert the object to a jsonable-version to send as request
    # if id_only is true, return only the most important attributes
    # (e.g. to avoid recursion)
    # things like converting dates to bugzilla-representation or attachment-data
    # to base64 should happen here
    def to_json(self, id_only = False):
        raise RuntimeError("Subclasses have to implement this method")

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
        return self._get("bug/attachment/" + attachment_id, **kw)["attachments"][attachment_id]

if __name__ == "__main__":
    b = Bugzilla("http://bugzilla.mozilla.org/")
    print(b.get_attachment(23))