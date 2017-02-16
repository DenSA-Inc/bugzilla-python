import json
from base64 import b64decode
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from .objects import *
from .util import parse_bugzilla_datetime

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
        self.api_key = api_key
        self.charset = "utf-8" # i have to lookup the right charset, until then utf-8 should suffice
    
    def _get(self, path, **kw):
        return self._read_request("GET", path, None, **kw)
    
    def _post(self, path, data, **kw):
        return self._read_request("POST", path, data, **kw)
    
    def _put(self, path, data, **kw):
        return self._read_request("PUT", path, data, **kw)
    
    def _read_request(self, method, path, post_data, **kw):
        if self.api_key:
            kw["api_key"] = self.api_key
        # sequences supplied for the in/exclude_fields will automatically be comma-joined
        if not isinstance(kw.get("include_fields", ""), str):
            kw["include_fields"] = ",".join(kw["include_fields"])
        if not isinstance(kw.get("exclude_fields", ""), str):
            kw["exclude_fields"] = ",".join(kw["exclude_fields"])
        
        if post_data is not None: post_data = json.dumps(post_data).encode("utf-8")
        
        query = urlencode(kw, True)
        if query: query = "?" + query
        url = self.url + path + query
        try:
            request = Request(url, post_data)
            request.get_method = lambda: method
            if post_data is not None:
                request.add_header("Content-type", "application/json")
            
            data = urlopen(request).read()
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
    
    def _get_attachment(self, data):
        if "creation_time" in data: data["creation_time"] = parse_bugzilla_datetime(data["creation_time"])
        if "last_change_time" in data: data["last_change_time"] = parse_bugzilla_datetime(data["last_change_time"])
        if "data" in data: data["data"] = b64decode(data["data"])
        if "size" in data: del data["size"]
        if "is_private" in data: data["is_private"] = bool(data["is_private"])
        if "is_obsolete" in data: data["is_obsolete"] = bool(data["is_obsolete"])
        if "is_patch" in data: data["is_patch"] = bool(data["is_patch"])
        if "flags" in data: data["flags"] = [self._get_flag(obj) for obj in data["flags"]]
        
        return Attachment(data)
    
    def _get_flag(self, data):
        if "creation_date" in data: data["creation_date"] = parse_bugzilla_datetime(data["creation_date"])
        if "modification_date" in data: data["modification_date"] = parse_bugzilla_datetime(data["modification_date"])
        
        return Flag(data)
    
    def _get_bug(self, data):
        if "creation_time" in data: data["creation_time"] = parse_bugzilla_datetime(data["creation_time"])
        if "flags" in data: data["flags"] = [self._get_flag(obj) for obj in data["flags"]]
        if "is_cc_accessible" in data: data["is_cc_accessible"] = bool(data["is_cc_accessible"])
        if "is_confirmed" in data: data["is_confirmed"] = bool(data["is_confirmed"])
        if "is_open" in data: data["is_open"] = bool(data["is_open"])
        if "is_creator_accessible" in data: data["is_creator_accessible"] = bool(data["is_creator_accessible"])
        if "last_change_time" in data: data["last_change_time"] = parse_bugzilla_datetime(data["last_change_time"])
        
        return Bug(data)
    
    def _get_history(self, data):
        if "when" in data: data["when"] = parse_bugzilla_datetime(data["when"])
        if "changes" in data: data["changes"] = [Change(obj) for obj in data["changes"]]
        
        return History(data)
    
    def _get_product(self, data):
        if "components" in data: data["components"] = [self._get_component(obj) for obj in data["components"]]
        if "versions" in data: data["versions"] = [self._get_version(obj) for obj in data["versions"]]
        if "milestones" in data: data["milestones"] = [self._get_milestone(obj) for obj in data["milestones"]]
        
        return Product(data)
    
    def _get_component(self, data):
        if "flag_types" in data:
            data["flag_types"]["bug"] = [self._get_flag_type(obj) for obj in data["flag_types"]["bug"]]
            data["flag_types"]["attachment"] = [self._get_flag_type(obj) for obj in data["flag_types"]["attachment"]]
        
        return Component(data)
    
    def _get_flag_type(self, data):
        return FlagType(data)
    
    def _get_version(self, data):
        return Version(data)
    
    def _get_milestone(self, data):
        return Milestone(data)
    
    def _get_classification(self, data):
        return Classification(data)
    
    def _get_update_result(self, data):
        if "last_change_time" in data: data["last_change_time"] = parse_bugzilla_datetime(data["last_change_time"])
        
        return UpdateResult(data)
    
    def get_version(self):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bugzilla.html'
        return self._get("version")["version"]
    
    def get_extensions(self):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bugzilla.html'
        return self._get("extensions")["extensions"]
    
    def get_time(self):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bugzilla.html'
        data = self._get("time")
        data["db_time"] = parse_bugzilla_datetime(data["db_time"])
        data["web_time"] = parse_bugzilla_datetime(data["web_time"])
        
        return data
    
    def get_parameters(self, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bugzilla.html'
        return self._get("parameters", **kw)["parameters"]
    
    def get_last_audit_time(self, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bugzilla.html'
        return parse_bugzilla_datetime(self._get("last_audit_time", **kw)["last_audit_time"])
    
    def get_attachment(self, attachment_id, **kw):
        'https://bugzilla.readthedocs.io/en/5.0/api/core/v1/attachment.html'
        attachment_id = str(attachment_id)
        return self._get_attachment(self._get("bug/attachment/" + attachment_id, **kw)["attachments"][attachment_id])
    
    def get_attachments_by_bug(self, bug, **kw):
        'https://bugzilla.readthedocs.io/en/5.0/api/core/v1/attachment.html'
        bug_id = str(bug.id if isinstance(bug, Bug) else bug)
        return [self._get_attachment(data) for data in self._get("bug/%s/attachment" % bug_id, **kw)["bugs"][bug_id]]
    
    def get_bug(self, bug_id, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug.html'
        bug_id = str(bug_id)
        return self._get_bug(self._get("bug/" + bug_id, **kw)["bugs"][0])
    
    def search_bugs(self, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug.html'
        return [self._get_bug(data) for data in self._get("bug", **kw)["bugs"]]
    
    def get_bug_history(self, bug_id, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug.html'
        bug_id = str(bug_id)
        return [self._get_history(history) for history in self._get("bug/" + bug_id + "/history", **kw)["bugs"][0]["history"]]
    
    def get_selectable_product_ids(self):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/product.html'
        return sorted(map(int, self._get("product_selectable")["ids"]))
    
    def get_accessible_product_ids(self):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/product.html'
        return sorted(map(int, self._get("product_accessible")["ids"]))
    
    def get_enterable_product_ids(self):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/product.html'
        return sorted(map(int, self._get("product_enterable")["ids"]))
    
    def get_product(self, product_id, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/product.html'
        product_id = str(product_id)
        return self._get_product(self._get("product/" + product_id, **kw)["products"][0])
    
    def get_classification(self, c_id, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/classification.html'
        c_id = str(c_id)
        return [self._get_classification(obj) for obj in self._get("classification/" + c_id, **kw)["classifications"]]
    
    def get_last_visited(self, bug_ids = None, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug-user-last-visit.html'
        if not self.api_key:
            raise BugzillaException(-1, "You must be logged in to use that method")
        
        if bug_ids is None or isinstance(bug_ids, int):
            url = "bug_user_last_visit/" + ("" if bug_ids is None else str(bug_ids))
        else:
            url = "bug_user_last_visit/" + str(bug_ids[0])
            kw["ids"] = bug_ids[1:]
        
        return self._get(url, **kw)
    
    def update_last_visited(self, bug_ids, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug-user-last-visit.html'
        if not self.api_key:
            raise BugzillaException(-1, "You must be logged in to use that method")
        
        if isinstance(bug_ids, int):
            url = "bug_user_last_visit/" + str(bug_ids)
            data = None
        else:
            url = "bug_user_last_visit"
            data = bug_ids
        
        return self._post(url, data, **kw)
    
    def add_attachment(self, attachment, ids, comment = ""):
        'https://bugzilla.readthedocs.io/en/5.0/api/core/v1/attachment.html'
        if isinstance(ids, int): ids = [ids]
        
        if not attachment.can_be_added():
            raise BugzillaException(-1, "This attachment does not have the required fields set")
        data = attachment.add_json()
        data["ids"] = ids
        data["comment"] = comment
        return [int(i) for i in self._post("bug/%i/attachment" % ids[0], data)["ids"]]
    
    def update_attachment(self, attachment, ids = None, comment = ""):
        'https://bugzilla.readthedocs.io/en/5.0/api/core/v1/attachment.html'
        if ids is None: ids = attachment.id
        if isinstance(ids, int): ids = [ids]
        
        if not attachment.can_be_updated():
            raise BugzillaException(-1, "This attachment does not have the required fields set")
        data = attachment.update_json()
        data["ids"] = ids
        data["comment"] = comment
        return [self._get_update_result(obj) for obj in self._put("bug/attachment/%i" % ids[0], data)["attachments"]]
    
    def add_bug(self, bug, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug.html'
        if not bug.can_be_added():
            raise BugzillaException(-1, "This attachment does not have the required fields set")
        
        data = bug.add_json()
        data.update(kw)
        return int(self._post("bug", data)["id"])
