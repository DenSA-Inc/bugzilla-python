import json
from base64 import b64decode
from urllib.parse import urlencode, quote_plus
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
        self.charset = "utf-8"
    
    def get_api_key(self):
        return self.api_key
    
    def set_api_key(self, key):
        self.api_key = key
    
    # a little helper function to encode url-parameters
    def _quote(self, string):
        return quote_plus(string)
    
    def _get(self, path, **kw):
        return self._read_request("GET", path, None, **kw)
    
    def _post(self, path, data, **kw):
        return self._read_request("POST", path, data, **kw)
    
    def _put(self, path, data, **kw):
        return self._read_request("PUT", path, data, **kw)
    
    def _delete(self, path, data, **kw):
        return self._read_request("DELETE", path, data, **kw)
    
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
        
        if isinstance(obj, dict) and obj.get("error"):
            raise BugzillaException(obj["code"], obj["message"])
        
        return obj
    
    def _map(self, dct, key, func):
        if key in dct:
            if isinstance(dct[key], list):
                dct[key] = [func(obj) for obj in dct[key]]
            else:
                dct[key] = func(dct[key])
    
    def _get_attachment(self, data):
        self._map(data, "creation_time", parse_bugzilla_datetime)
        self._map(data, "last_change_time", parse_bugzilla_datetime)
        self._map(data, "data", b64decode)
        self._map(data, "is_private", bool)
        self._map(data, "is_obsolete", bool)
        self._map(data, "is_patch", bool)
        self._map(data, "flags", self._get_attachment_flag)
        if "size" in data: del data["size"]
        
        return Attachment(data)
    
    def _get_attachment_flag(self, data):
        self._map(data, "creation_date", parse_bugzilla_datetime)
        self._map(data, "modification_date", parse_bugzilla_datetime)
        
        return AttachmentFlag(data)
    
    def _get_bug(self, data):
        self._map(data, "creation_time", parse_bugzilla_datetime)
        self._map(data, "flags", self._get_attachment_flag)
        self._map(data, "is_cc_accessible", bool)
        self._map(data, "is_confirmed", bool)
        self._map(data, "is_open", bool)
        self._map(data, "is_creator_accessible", bool)
        self._map(data, "last_change_time", parse_bugzilla_datetime)
        
        return Bug(data)
    
    def _get_history(self, data):
        self._map(data, "when", parse_bugzilla_datetime)
        self._map(data, "changes", Change)
        
        return History(data)
    
    def _get_product(self, data):
        self._map(data, "components", self._get_component)
        self._map(data, "versions", self._get_version)
        self._map(data, "milestones", self._get_milestone)
        
        return Product(data)
    
    def _get_component(self, data):
        if "flag_types" in data:
            self._map(data["flag_types"], "bug", self._get_flag_type)
            self._map(data["flag_types"], "attachment", self._get_flag_type)
        
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
        self._map(data, "last_change_time", parse_bugzilla_datetime)
        
        return UpdateResult(data)
    
    def _get_comment(self, data):
        self._map(data, "time", parse_bugzilla_datetime)
        self._map(data, "creation_time", parse_bugzilla_datetime)
        
        return Comment(data)
    
    def _get_field(self, data):
        self._map(data, "values", BugFieldValue)
        
        return BugField(data)
    
    def _get_user(self, data):
        self._map(data, "groups", self._get_group)
        self._map(data, "saved_searches", Search)
        self._map(data, "saved_reports", Search)
        
        return User(data)
    
    def _get_group(self, data):
        self._map(data, "membership", self._get_user)
        
        return Group(data)
    
    def get_version(self):
        """
        Gets the bugzilla-version, usually in the format X.X or X.X.X
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bugzilla.html#version
        """
        return self._get("version")["version"]
    
    def get_extensions(self):
        """
        Gets all the installed extensions. Returns a dict in which the keys describe
        the extension name, the values are also a dict. The value has one key, "version",
        containing the extension-version.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bugzilla.html#extensions
        """
        return self._get("extensions")["extensions"]
    
    def get_time(self):
        """
        Returns the local times for the bugzilla web- and the database-server. The return
        value is a dict, in which the key "db_time" refers to the database-time and the
        key "web_time" refers to the webserver-time. Also, older versions of bugzilla
        might return more fields. For that refer to the documentation-link provided.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bugzilla.html#time
        """
        data = self._get("time")
        self._map(data, "db_time", parse_bugzilla_datetime)
        self._map(data, "web_time", parse_bugzilla_datetime)
        self._map(data, "web_time_utc", parse_bugzilla_datetime)
        
        return data
    
    def get_parameters(self, **kw):
        """
        Returns a dict containing the configuration-parameters of the bugzilla-instance.
        If no api-key is specified only a few parameters will be returned. For a
        complete list of parameters see the link.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bugzilla.html#parameters
        """
        return self._get("parameters", **kw)["parameters"]
    
    def get_last_audit_time(self, class_ = None):
        """
        Returns the last audit time for a given class. The class can be "Bugzilla::Component"
        or something similar. Appearently, if no class is given, "Bugzilla::Product" will be
        assumed.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bugzilla.html#last-audit-time
        """
        kw = {}
        if class_ is not None: kw["class"] = class_
        return parse_bugzilla_datetime(self._get("last_audit_time", **kw)["last_audit_time"])
    
    def get_attachment(self, attachment_id, **kw):
        """
        Returns the attachment with the given id. The id has to be an int.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/attachment.html#get-attachment
        """
        return self._get_attachment(self._get("bug/attachment/%i" % attachment_id, **kw)["attachments"][str(attachment_id)])
    
    def get_attachments_by_bug(self, bug, **kw):
        """
        Returns the attachment for a given bug. The parameter bug can be a bug-object,
        a bug-id or a bug-alias.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/attachment.html#get-attachment
        """
        bug_id = str(bug.id if isinstance(bug, Bug) else bug)
        return [self._get_attachment(data) for data in self._get("bug/%s/attachment" % self._quote(bug_id), **kw)["bugs"][bug_id]]
    
    def get_bug(self, bug_id, **kw):
        """
        Returns the bug for the given id. The parameter bug_id can be a numeric id or
        a bug alias.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug.html#get-bug
        """
        bug_id = str(bug_id)
        return self._get_bug(self._get("bug/" + self._quote(bug_id), **kw)["bugs"][0])
    
    def search_bugs(self, **kw):
        """
        Search bugzilla for bugs. Several keyword-parameters can be passed to specify your search.
        Because of my lazyness you have to click the link below.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug.html#search-bugs
        """
        return [self._get_bug(data) for data in self._get("bug", **kw)["bugs"]]
    
    def get_bug_history(self, bug_id, **kw):
        """
        Return the history for a specific bug. The bug_id can be a numeric id or a bug-alias.
        The optional keyword-parameter new_since can be passed to only get the history after
        a specific date (must be an encoded date, NO DATETIME)
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug.html#bug-history
        """
        bug_id = str(bug_id)
        return [self._get_history(history) for history in self._get("bug/%s/history" % self._quote(bug_id), **kw)["bugs"][0]["history"]]
    
    def get_selectable_product_ids(self):
        """
        Return a list of selectable product's ids.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/product.html#list-products
        """
        return sorted(map(int, self._get("product_selectable")["ids"]))
    
    def get_accessible_product_ids(self):
        """
        Returns a list of accessible product's ids
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/product.html#list-products
        """
        return sorted(map(int, self._get("product_accessible")["ids"]))
    
    def get_enterable_product_ids(self):
        """
        Returns a list of enterable product's ids
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/product.html#list-products
        """
        return sorted(map(int, self._get("product_enterable")["ids"]))
    
    def get_product(self, product_id = None, **kw):
        """
        Get products by id or search paramters. The product_id can be a product-id or a
        product-name. Optional keyword-parameters are:
        ids: A list of ids to get the products for
        names: A list of product-names to get the corresponding products
        type: A product type, can be "accessible", "selectable" or "enterable".
            It can be a list containing multible of these values.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/product.html#get-product
        """
        path = "product"
        if product_id is not None: path += "/" + self._quote(product_id)
        return self._get_product(self._get(path, **kw)["products"][0])
    
    def get_classification(self, c_id, **kw):
        """
        Get a classification by its numeric id or name. The parameter c_id can be both.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/classification.html#get-classification
        """
        c_id = str(c_id)
        return [self._get_classification(obj) for obj in self._get("classification/" + self._quote(c_id), **kw)["classifications"]]
    
    def get_comments_by_bug(self, bug_id, **kw):
        """
        Get the list of comments for a given bug. The parameter bug_id can be a bug-object, a bug-id
        or a bug-alias. The optional parameter new_since can be passed to filter for comments
        after this datetime. The parameter has to be an encoded datetime.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/comment.html#get-comments
        """
        bug_id = str(bug.id if isinstance(bug, Bug) else bug)
        return [self._get_comment(obj) for obj in self._get("bug/%s/comment" % self._quote(bug_id), **kw)["bugs"][bug_id]["comments"]]
    
    def get_comment(self, c_id, **kw):
        """
        Gets the comment with the given id. The id has to be an int. This method has two
        optional keyword-parameters:
        comment_ids: A list of comment_ids to get additional comments
        ids: A list of bug-ids to get additional comments for
        new_since: Filter and only return comments after a specific datetime. The value for this
            parameter has to be an encoded datetime.
        Note that comment_ids overwrites new_since, comments with ids from comment_ids will be
        returned even if they are older than new_since.
        If only c_id is given a comment is returned, otherwise a list of comments.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/comment.html#get-comments
        """
        data = self._get("bug/comment/%i" % c_id, **kw)
        comments = [self._get_comment(data["comments"][key]) for key in data["comments"]]
        for bug_id in data["bugs"]:
            comments.extend(self._get_comment(obj) for obj in data["bugs"][bug_id]["comments"])
        
        if not kw:
            return comments[0] # only the id was given
        else:
            return comments
    
    def search_comment_tags(self, query, **kw):
        """
        Search for tags which contain the given substring. The keyword-parameter limit
        specifies the maximum number of results. It defaults to 10.
        A list of strings is returned.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/comment.html#search-comment-tags
        """
        return self._get("bug/comment/tags/" + self._quote(query), **kw)
    
    def get_last_visited(self, bug_ids = None, **kw):
        """
        Get the last-visited timestamp for one or multiple bugs. The parameter bug_ids
        can be a bug-id, a list of bug-ids or not set if you want the last 20 visited bugs.
        The return value is a list of dicts, each containing the keys "id" (the bug id)
        and "last_visit_ts" (the last-visit-timestamp)
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/bug-user-last-visit.html#get-last-visited
        """
        if bug_ids is None or isinstance(bug_ids, int):
            url = "bug_user_last_visit" + ("" if bug_ids is None else "/" str(bug_ids))
        else:
            url = "bug_user_last_visit/%i" % bug_ids[0]
            kw["ids"] = bug_ids[1:]
        
        data = self._get(url, **kw)
        for obj in data: self._map(data, "last_visit_ts", parse_bugzilla_datetime)
        return data
    
    def get_fields(self, id_or_name = None, **kw):
        """
        Get all fields or a specific one. To specify a field, pass its id or name
        as parameter.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/field.html#fields
        """
        path = "field/bug"
        if id_or_name is not None: path += "/" + self._quote(str(id_or_name))
        
        return [self._get_field(field) for field in self._get(path, **kw)["fields"]]
    
    def get_user(self, user_id = None, **kw):
        """
        Get one or multiple users. If user_id is given (which can be a numeric id or an
        user name) only one user will be searched for and a single user will be returned.
        By passing one or more keyword-parameters multiple users will be searched for
        and the return value will be a list.
        Valid keyword-parameters are:
        ids: A list of user-ids. You have to be logged in to use this.
        names: A list of user-names.
        match: A list of strings. Bugzilla will search for users whose login-name or
            real-name contains one of these strings. You have to be logged in to use that.
        limit: A limit of users matched by the match-parameter. Be vary that bugzilla
            itself has its own limit and will use it if your limit is higher.
        group_ids: A list of group-ids that users can be in.
        groups: Same as group_ids.
        include_disabled: include disabled users, even if the do not match the match-parameter
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/user.html#get-user
        """
        path = "user" if user_id is None else "user/" + self._quote(str(user_id))
        users = [self._get_user(data) for data in self._get(path, **kw)["users"]]
        if not kw: # only an id or name was given
            return users[0]
        else:
            return users
    
    def get_flag_types(self, product, component = None, **kw):
        """
        Get flag-types for a product and optionally a products component.
        As for now, both parameters have to be strings, the products and components
        name respectively.
        https://bugzilla.readthedocs.io/en/5.0/api/core/v1/flagtype.html#get-flag-type
        """
        path = "flag_types/" + self._quote(product)
        if component is not None: path += "/" + self._quote(component)
        
        data = self._get(path, **kw)
        if "bug" in data: data["bug"] = [self._get_flag_type(obj) for obj in data["bug"]]
        if "attachment" in data: data["attachment"] = [self._get_flag_type(obj) for obj in data["attachment"]]
        
        return data
    
    def get_attachment_flag_types(self, product, component = None, **kw):
        """
        Get flag-types as in get_flag_types, but limit the return value to the
        attachment-flag-types. All parameters are the same as in get_flag_types.
        """
        return self.get_flag_types(product, component, **kw)["attachment"]
    
    def get_bug_flag_types(self, product, component = None, **kw):
        """
        Get flag-types as in get_flag_types, but limit the return value to the
        bug-flag-types. All parameters are the same as in get_flag_types.
        """
        return self.get_flag_types(product, component, **kw)["bug"]
    
    # there are several possible parameters to this method
    # these are ids, names, match, limit, group_ids, groups, include_disabled
    def search_users(self, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/user.html#get-user'
        return [self._get_user(data) for data in self._get("user", **kw)["users"]]
    
    def whoami(self, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/user.html#who-am-i'
        return User(self._get("whoami", **kw))
    
    def get_group(self, group_id, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/group.html#get-group'
        # TODO: find the solution
        # for some reason, bugzilla 5.0 does not find the resource, so this workaround has to do
        # this was the original code:
        # group_id = str(group_id)
        # return [self._get_group(data) for data in self._get("group/" + self._quote(group_id), **kw)["groups"]][0]
        if isinstance(group_id, str):
            return self.search_groups(names = [group_id], **kw)[0]
        else:
            return self.search_groups(ids = [group_id], **kw)[0]
    
    def search_groups(self, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/group.html#get-group'
        return [self._get_group(data) for data in self._get("group", **kw)["groups"]]
    
    def update_last_visited(self, bug_ids, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug-user-last-visit.html'
        if not self.api_key:
            raise BugzillaException(-1, "You must be logged in to use that method")
        
        if isinstance(bug_ids, int):
            url = "bug_user_last_visit/" + str(bug_ids)
            data = None
        else:
            url = "bug_user_last_visit"
            data = {"ids": bug_ids}
        
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
            raise BugzillaException(-1, "This bug does not have the required fields set")
        
        data = bug.add_json()
        data.update(kw)
        return int(self._post("bug", data)["id"])
    
    # since there are so many array fields that are updated via an add/remove/set-object,
    # this method has 3 additional parameters.
    # specifying add = {"keywords": ["key", "word"]} will result in {"keywords": {"add": ["key", "word"]}}
    # in the final update-object. These parameters will be removed once I find a better way.
    # Note: these 3 parameters overwrite keyword-parameters
    # TODO: find a better way.
    def update_bug(self, bug, ids = None, add = {}, remove = {}, set_ = {}, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/bug.html#update-bug'
        if ids is None: ids = bug.id
        if isinstance(ids, int): ids = [ids]
        
        # the use of add/remove and set at the same time is not permitted
        if (set(add.keys()) | set(remove.keys())) & set(set_.keys()):
            raise ValueError("You can not use the same keys in _set and add/remove")
        asr = {} # no, you find a better variable name
        for key in (set(add.keys()) | set(remove.keys())): asr[key] = {}
        for key in add: asr[key]["add"] = add[key]
        for key in remove: asr[key]["remove"] = remove[key]
        for key in set_: asr[key] = {"set": set_[key]}
        
        if not bug.can_be_updated():
            raise BugzillaException(-1, "This bug does not have the required fields set")
        data = bug.update_json()
        data["ids"] = ids
        data.update(kw)
        data.update(asr)
        return [self._get_update_result(obj) for obj in self._put("bug/%i" % ids[0], data)["bugs"]]
    
    def add_comment(self, comment, bug_id, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/comment.html'
        if not comment.can_be_added():
            raise BugzillaException(-1, "This comment does not have the required fields set")
        
        bug_id = str(bug_id)
        data = comment.add_json()
        data.update(kw)
        return int(self._post("bug/%s/comment" % self._quote(bug_id), data)["id"])
    
    def update_comment_tags(self, comment_id, add = [], remove = []):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/comment.html'
        comment_id = str(comment_id)
        data = {"comment_id": comment_id, "add": add, "remove": remove}
        return self._put("bug/comment/%s/tags" % comment_id, data)
    
    # there are several parameters you can pass to this method
    # these are product, default_cc and is_open
    # the product-parameter is mandatory
    def add_component(self, component, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/component.html#create-component'
        if not component.can_be_added():
            raise BugzillaException(-1, "This component does not have the required fields set")
        
        data = component.add_json()
        data.update(kw)
        return int(self._post("component", data)["id"])
    
    # both of the methods are not tested yet because i was too lazy to install the latest version
    def update_component(self, component, product = None, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/component.html#update-component'
        data = component.update_json()
        if product is None:
            path = str(component.id)
            data["ids"] = component.id
        else:
            path = self._quote(product) + "/" + self._quote(component.name)
            data["names"] = [{"product": product, "component": component.name}]
        
        data.update(kw)
        return self._put("component/" + path, data)["components"]
    
    def delete_component(self, component_id, product = None):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/component.html#delete-component'
        if product is None:
            path = str(component_id)
        else:
            path = self._quote(product) + "/" + self._quote(str(component_id))
        
        return self._delete("component/" + path, None)["components"][0]["id"]
    
    def add_group(self, group, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/group.html#create-group'
        if not group.can_be_added():
            raise BugzillaException(-1, "This group does not have the required fields set")
        
        data = group.add_json()
        data.update(kw)
        return int(self._post("group", data)["id"])
    
    def update_group(self, group, ids = None, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/group.html#update-group'
        if ids is None: ids = group.id
        if isinstance(ids, int): ids = [ids]
        
        if not group.can_be_updated():
            raise BugzillaException(-1, "This group does not have the required fields set")
        data = group.update_json()
        data.update(kw)
        data["ids"] = ids
        return [UpdateResult(data) for data in self._put("group/%i" % ids[0], data)["groups"]]
    
    def add_user(self, user, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/user.html#create-user'
        if not user.can_be_added():
            raise BugzillaException(-1, "This user does not have the required fields set")
        data = user.add_json()
        data.update(kw)
        return int(self._post("user", data)["ids"])
    
    # TODO: until now, the group-objects for this call have to be crafted yourself.
    # find some way to make this more elegant
    def update_user(self, user, ids = None, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/user.html#update-user'
        if ids is None: ids = user.id
        if isinstance(ids, int): ids = [ids]
        
        if not user.can_be_updated():
            raise BugzillaException(-1, "This user does not have the required fields set")
        data = user.update_json()
        data["ids"] = ids
        data.update(kw)
        return [UpdateResult(data) for data in self._put("user/%i" % ids[0], data)["users"]]
    
    def add_product(self, product, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/product.html#create-product'
        if not product.can_be_added():
            raise BugzillaException(-1, "This product does not have the required fields set")
        data = product.add_json()
        data.update(kw)
        return int(self._post("product", data)["ids"])
    
    def update_product(self, product, ids = None, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/product.html#update-product'
        if ids is None: ids = product.id
        if isinstance(ids, int): ids = [ids]
        
        if not product.can_be_updated():
            raise BugzillaException(-1, "This product does not have the required fields set")
        data = product.update_json()
        data["ids"] = ids
        data.update(kw)
        return [UpdateResult(data) for data in self._put("product/%i" % ids[0], data)["products"]]
    
    # look at the link for the additional fields that have to be/can be set.
    # target_type is mandatory, also have a look at inclusions and exclusions
    def add_flag_type(self, flag_type, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/flagtype.html#create-flag-type'
        if not flag_type.can_be_added():
            raise BugzillaException(-1, "This FlagType does not have the required fields set")
        data = flag_type.add_json()
        data.update(kw)
        return int(self._post("flag_type", data)["ids"])
    
    def update_flag_type(self, flag_type, ids = None, **kw):
        'https://bugzilla.readthedocs.io/en/latest/api/core/v1/flagtype.html#update-flag-type'
        if ids is None: ids = flag_type.id
        if isinstance(ids, int): ids = [ids]
        
        if not flag_type.can_be_updated():
            raise BugzillaException(-1, "This product does not have the required fields set")
        data = flag_type.update_json()
        data["ids"] = ids
        data.update(kw)
        return [UpdateResult(data) for data in self._put("flag_type/%i" % ids[0], data)["flagtypes"]]
