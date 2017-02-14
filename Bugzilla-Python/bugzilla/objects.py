import base64
from .util import encode_bugzilla_datetime
from copy import deepcopy

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
    
    def set_default_attributes(self, attributes):
        for key, value in deepcopy(attributes).items():
            self.setdefault(key, value)

# Note that this class has a lot of _detail-fields. To avoid unnecessary lines of code,
# the none-_detail-fields will just refer to the _detail-fields. E.g. creator wil look up
# creator_detail. That way, setting creator_detail is enough to set both fields.
class Bug(BugzillaObject):
    ATTRIBUTES = {
        "alias": [],
        "assigned_to_detail": None,
        "blocks": [],
        "cc_detail": [],
        "classification": "",
        "component": "",
        "creation_time": None,
        "creator_detail": None,
        "deadline": None,
        "depends_on": [],
        "dupe_of": None,
        "flags": [],
        "groups": [],
        "id": -1,
        "is_cc_accessible": False,
        "is_confirmed": False,
        "is_open": False,
        "is_creator_accessible": False,
        "keywords": [],
        "last_change_time": None,
        "op_sys": "",
        "platform": "",
        "priority": "",
        "product": "",
        "qa_contact_detail": None,
        "resolution": "",
        "see_also": [],
        "severity": "",
        "status": "",
        "summary": "",
        "target_milestone": "",
        "url": "",
        "version": "",
        "whiteboard": ""
    }
    
    def __init__(self, attributes):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Bug.ATTRIBUTES)
    
    def __getattr__(self, attr):
        if attr == "assigned_to": return None if self.assigned_to_detail is None else self.assigned_to_detail["name"]
        elif attr == "cc": return [None if cc_detail is None else cc_detail["name"] for cc_detail in self.cc_detail]
        elif attr == "creator": return None if self.creator_detail is None else self.creator_detail["name"]
        
        return BugzillaObject.__getattr__(self, attr)
    
    def __setattribute__(self, attr, value):
        if attr in ("assigned_to", "cc", "creator"):
            raise AttributeError("The virtual attribute '%s' cannot be overwritten")
        
        BugzillaObject.__setattribute__(self, attr, value)
    
    def to_json(self, id_only = False):
        if id_only:
            return self.id
        
        obj = dict(self)
        obj["assigned_to"] = self.assigned_to
        obj["blocks"] = [block.to_json(True) for block in self.blocks]
        obj["cc"] = self.cc
        obj["creation_time"] = encode_bugzilla_datetime(self.creation_time)
        obj["creator"] = self.creator
        obj["flags"] = [flag.to_json() for flag in self.flags]
        obj["last_change_time"] = encode_bugzilla_datetime(self.last_change_time)
        obj["qa_contact"] = self.qa_contact
        
        return obj

class Product(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "name": "",
        "description": "",
        "is_active": False,
        "default_milestone": "",
        "has_unconfirmed": False,
        "classification": "",
        "components": [],
        "versions": [],
        "milestones": []
    }
    
    def __init__(self, attributes):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Product.ATTRIBUTES)
    
    def to_json(self, id_only = False):
        obj = dict(self)
        obj["components"] = [component.to_json() for component in self.components]
        obj["versions"] = [version.to_json() for version in self.versions]
        obj["milestones"] = [milestone.to_json() for milestone in self.milestones]
        
        return obj

class Component(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "name": "",
        "description": "",
        "default_assigned_to": "",
        "default_qa_contact": "",
        "sort_key": 0,
        "is_active": False,
        "flag_types": {
            "bug": [],
            "attachment": []
        }
    }
    
    def __init__(self, attributes):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Component.ATTRIBUTES)
    
    def to_json(self, id_only = False):
        obj = dict(self)
        obj["flag_types"] = dict(self.flag_types)
        obj["flag_types"]["bug"] = [ft.to_json() for ft in self.flag_types["bug"]]
        obj["flag_types"]["attachment"] = [ft.to_json() for ft in self.flag_types["attachment"]]
        
        return obj

class FlagType(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "name": "",
        "description": "",
        "cc_list": [],
        "sort_key": 0,
        "is_active": False,
        "is_requestable": False,
        "is_requesteeble": False,
        "is_multiplicable": False,
        "grant_group": None,
        "request_group": None
    }
    
    def __init__(self, attributes):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(FlagType.ATTRIBUTES)
    
    def to_json(self, id_only = False):
        return dict(self) # TODO: think about how to handle the group-fields an the list (reference-problem)

class Version(BugzillaObject):
    ATTRIBUTES = {
        "name": "",
        "sort_key": "",
        "is_active": False
    }
    
    def __init__(self, attributes):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Version.ATTRIBUTES)
    
    def to_json(self, id_only = False):
        return dict(self)

class Milestone(BugzillaObject):
    ATTRIBUTES = {
        "name": "",
        "sort_key": "",
        "is_active": False
    }
    
    def __init__(self, attributes):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Milestone.ATTRIBUTES)
    
    def to_json(self, id_only = False):
        return dict(self)

class Classification(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "name": "",
        "description": "",
        "sort_key": 0,
        "products": []
    }
    
    def __init__(self, attributes):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Classification.ATTRIBUTES)
    
    def to_json(self, id_only = False):
        return dict(self)

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
        self.set_default_attributes(Attachment.ATTRIBUTES)
    
    def __getattr__(self, attr):
        # to avoid the trouble of setting the size along with the data, size is
        # a virtual attribute
        if attr == "size":
            return len(self.data)
        else:
            return BugzillaObject.__getattr__(self, attr)
    
    def __setattribute__(self, attr, value):
        if attr == "size":
            raise AttributeError("The virtual attribute 'size' cannot be overwritten")
        
        BugzillaObject.__setattribute__(self, attr, value)
    
    def to_json(self, id_only = False):
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
        self.set_default_attributes(Flag.ATTRIBUTES)
    
    def to_json(self, id_only = False):
        obj = dict(self)
        obj["creation_date"] = encode_bugzilla_datetime(self.creation_date)
        obj["modification_date"] = encode_bugzilla_datetime(self.modification_date)
        
        return obj
