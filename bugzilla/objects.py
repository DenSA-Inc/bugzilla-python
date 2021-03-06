import base64
from copy import deepcopy
from .util import encode_bugzilla_date

class BugzillaObject(dict):
    # Treat the object-attributes as dict-indizes for easier jsoning
    def __getattr__(self, attr):
        return self.__getitem__(attr)
    
    def __setattr__(self, attr, value):
        self.__setitem__(attr, value)
    
    def __delattr__(self, attr):
        self.__delitem__(attr)
    
    def __repr__(self):
        return "%s(%s)" % (type(self).__name__, dict.__repr__(self))
    
    # return a jsonable object that will be sent if the bugzilla object wants to
    # be added. This includes only fields that can be sent. Since classes have 
    # default 'invalid' values set in the constructor subclasses should check if
    # these values are 'invalid' and only return those values which are valid.
    # The id_only parameter is the same as in the to_json-method
    def add_json(self, id_only = False):
        raise RuntimeError("%s's cannot be added (maybe not yet)" % self.__class__.__name__)
    
    # check if all fields are set (and not the 'invalid' default value) and the object
    # can be added according to the bugzilla-documentation. If this method returns
    # False, trying to add the object to bugzilla will result in an error.
    def can_be_added(self):
        return False
    
    # returns a jsonable object that will be sent if the bugzilla object wants to
    # be updated. This method is similar to add_json, yet it might return other fields.
    def update_json(self, id_only = False):
        raise RuntimeError("%s's cannot be added (maybe not yet)" % self.__class__.__name__)
    
    # similiar to can_be_added, this method returns True if the object can be added,
    # False otherwise. Most subclasses will return True if the id is valid and the
    # class can be updated in general.
    # if this method returns False trying to update will result in an error
    def can_be_updated(self):
        return False
    
    def set_default_attributes(self, attributes):
        for key, value in deepcopy(attributes).items():
            self.setdefault(key, value)

# Note that this class has a lot of _detail-fields. To avoid unnecessary lines of code,
# the none-_detail-fields will just refer to the _detail-fields. E.g. creator wil look up
# creator_detail. That way, setting creator_detail is enough to set both fields.
class Bug(BugzillaObject):
    # I'm currently just assuming that all custom fields start with cf_
    # I'll check this later
    CUSTOM_FIELD_PREFIX = "cf_"
    
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
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Bug.ATTRIBUTES)
    
    def __getitem__(self, attr):
        if attr == "assigned_to": return None if self.assigned_to_detail is None else self.assigned_to_detail["name"]
        elif attr == "cc": return [None if cc_detail is None else cc_detail["name"] for cc_detail in self.cc_detail]
        elif attr == "creator": return None if self.creator_detail is None else self.creator_detail["name"]
        elif attr == "qa_contact": return None if self.qa_contact_detail is None else self.qa_contact_detail["name"]
        
        return BugzillaObject.__getitem__(self, attr)
    
    def __setitem__(self, attr, value):
        if attr in ("assigned_to", "cc", "creator", "qa_contact"):
            raise AttributeError("The virtual attribute '%s' cannot be overwritten")
        
        BugzillaObject.__setitem__(self, attr, value)
    
    def add_json(self, id_only = False):
        dct = {}
        for field in ("product", "component", "summary", "version", "op_sys",
                    "platform", "priority", "severity", "alias", "assigned_to", "cc", "groups",
                    "keywords", "qa_contact", "status", "resolution", "target_milestone"):
            # fields will only be set if valid. since most fields here are string, they should
            # be valid if they are non-empty. they will not be copied by default because bugzilla
            # will require a valid value if set. (I had my problems with 'resolution')
            if self[field]: dct[field] = self[field]
        dct["flags"] = [flag.to_json() for flag in self.flags]
        dct.update(self.get_custom_fields())
        
        return dct
    
    def can_be_added(self):
        # beware that bugzilla might require more fields than those checked here
        # yet these are the only ones that are said to be required in the documentation
        # my bugzilla-installation (version 5.0) required much more fields
        return bool(self.product and self.component and self.summary and self.version)
    
    def update_json(self, id_only = False):
        dct = {}
        for field in ("assigned_to", "is_cc_accessible", "op_sys", "platform", "priority",
                    "qa_contact", "is_creator_accessible", "resolution", "severity", "status",
                    "summary", "url", "version", "whiteboard"):
            dct[field] = self[field]
        dct["deadline"] = encode_bugzilla_date(self.deadline)
        dct.update(self.get_custom_fields())
        return dct
    
    def can_be_updated(self):
        return self.id != -1
    
    def get_custom_fields(self):
        fields = {}
        for key, value in self.items():
            if key.startswith(Bug.CUSTOM_FIELD_PREFIX):
                fields[key] = value
        
        return fields

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
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Product.ATTRIBUTES)
    
    def add_json(self, id_only = False):
        dct = {}
        for field in ("name", "description", "version", "has_unconfirmed", "classification",
                    "default_milestone"):
            dct[field] = self[field]
        
        return dct
    
    def can_be_added(self):
        return bool(self.name and self.description and self.version)
    
    def update_json(self, id_only = False):
        dct = {}
        for field in ("name", "default_milestone", "description", "has_unconfirmed"):
            dct[field] = self[field]
        
        return dct
    
    def can_be_updated(self):
        return self.id != -1

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
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Component.ATTRIBUTES)
    
    def add_json(self, id_only = False):
        dct = {}
        for field in ("name", "description", "default_qa_contact"):
            if field: dct[field] = self[field]
        dct["default_assignee"] = self.default_assigned_to
        
        return dct
    
    def can_be_added(self):
        return bool(self.name and self.description and self.default_assigned_to)
    
    def update_json(self):
        dct = {}
        for field in ("name", "description", "default_qa_contact"):
            dct[field] = self[field]
        dct["default_assignee"] = self.default_assigned_to
        
        return dct
    
    def can_be_updated(self):
        return self.id != -1

# This object is tricky because different api-calls return different subsets of attributes
# If you want to find bugs, look here
class FlagType(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "name": "",
        "description": "",
        "cc_list": [],
        "sort_key": 0,
        "is_active": True,
        "is_requestable": True,
        "is_requesteeble": False,
        "is_multiplicable": True,
        "grant_group": None,
        "request_group": None,
        "type": "",
        "values": []
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(FlagType.ATTRIBUTES)
    
    def can_be_added(self):
        return bool(self.name and self.description)
    
    def add_json(self, id_only = False):
        dct = {}
        for field in ("name", "description", "is_active", "is_requestable", "cc_list",
                    "is_multiplicable"):
            dct[field] = self[field]
        for field in ("grant_group", "request_group"):
            if self[field]: dct[field] = self[field]
        
        if self.sort_key: dct["sortkey"] = self.sort_key # i blame the specs
        return dct
    
    def can_be_updated(self):
        return self.id != -1
    
    def update_json(self, id_only = False):
        return self.add_json()

class Version(BugzillaObject):
    ATTRIBUTES = {
        "name": "",
        "sort_key": "",
        "is_active": False
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Version.ATTRIBUTES)

class Milestone(BugzillaObject):
    ATTRIBUTES = {
        "name": "",
        "sort_key": "",
        "is_active": False
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Milestone.ATTRIBUTES)

class Classification(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "name": "",
        "description": "",
        "sort_key": 0,
        "products": []
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Classification.ATTRIBUTES)

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
    
    def __getitem__(self, attr):
        # to avoid the trouble of setting the size along with the data, size is
        # a virtual attribute
        if attr == "size":
            return len(self.data)
        else:
            return BugzillaObject.__getitem__(self, attr)
    
    def __setitem__(self, attr, value):
        if attr == "size":
            raise AttributeError("The virtual attribute 'size' cannot be overwritten")
        
        BugzillaObject.__setitem__(self, attr, value)
    
    def add_json(self, id_only = False):
        dct = {}
        for field in ("is_patch", "summary", "content_type", "file_name", "is_private"):
            dct[field] = self[field]
        
        dct["data"] = base64.b64encode(self.data).decode("ascii")
        dct["flags"] = []
        for flag in self.flags:
            flag_dct = {
                "name": flag.name,
                "type_id": flag.type_id,
                "status": flag.status
            }
            if flag.requestee: flag_dct["requestee"] = flag.requestee
            
            dct["flags"].append(flag_dct)
            
        return dct
    
    def can_be_added(self):
        return bool(self.file_name and self.summary and self.content_type)
    
    def update_json(self, id_only = False):
        dct = {}
        for field in ("file_name", "summary", "content_type", "is_patch", "is_private", "is_obsolete"):
            dct[field] = self[field]
        
        dct["flags"] = []
        for flag in self.flags:
            flag_dct = {
                "name": flag.name,
                "type_id": flag.type_id,
                "status": flag.status
            }
            if flag.requestee: flag_dct["requestee"] = flag.requestee
            
            dct["flags"].append(flag_dct)
        
        return dct
    
    def can_be_updated(self):
        return self.id != -1

class AttachmentFlag(BugzillaObject):
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
        self.set_default_attributes(AttachmentFlag.ATTRIBUTES)

class History(BugzillaObject):
    ATTRIBUTES = {
        "when": None,
        "who": "",
        "changes": []
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(History.ATTRIBUTES)

# Note: this class does not parse date/datetime-objects if they are passed to it.
# That is because the field-value will be a string and there is no way to determine
# the actual type of the field.
class Change(BugzillaObject):
    ATTRIBUTES = {
        "added": "",
        "removed": "",
        "field_name": ""
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Change.ATTRIBUTES)

# Note: Not many update-results have a last_change_time
class UpdateResult(BugzillaObject):
    ATTRIBUTES = {
        "changes": [],
        "id": -1,
        "last_change_time": None
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(UpdateResult.ATTRIBUTES)

class Comment(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "bug_id": -1,
        "attachment_id": None,
        "count": -1,
        "text": "",
        "creator": "",
        "time": None,
        "creation_time": None,
        "is_private": False,
        "is_markdown": False,
        "tags": []
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Comment.ATTRIBUTES)
    
    def add_json(self, id_only = False):
        dct = {}
        for field in ("is_private", "is_markdown"):
            dct[field] = self[field]
        
        dct["comment"] = self.text
        if self.tags: dct["comment_tags"] = self.tags
        return dct
    
    def can_be_added(self):
        return bool(self.text)

# Be careful with this one. values() is already a dict-method, you have to use obj["values"]
# to get the bug-field-values
class BugField(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "type": 0,
        "is_custom": False,
        "name": "",
        "display_name": "",
        "is_mandatory": False,
        "is_on_bug_entry": False,
        "visibility_field": None,
        "visibility_values": [],
        "value_field": None,
        "values": []
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(BugField.ATTRIBUTES)

class BugFieldValue(BugzillaObject):
    ATTRIBUTES = {
        "name": "",
        "sort_key": 0,
        "visibility_values": [],
        "is_active": False,
        "description": "",
        "is_open": False,
        "can_change_to": []
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(BugFieldValue.ATTRIBUTES)

class User(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "real_name": "",
        "email": "",
        "name": "",
        "can_login": True,
        "email_enabled": False,
        "login_denied_text": "",
        "groups": [],
        "saved_searches": [],
        "saved_reports": []
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(User.ATTRIBUTES)
    
    def add_json(self, id_only = False):
        return {
            "email": self.email,
            "full_name": self.real_name
        }
    
    def can_be_added(self):
        return bool(self.email)
    
    def update_json(self, id_only = False):
        dct = {}
        for field in ("email", "email_enabled", "login_denied_text"):
            dct[field] = self[field]
        dct["full_name"] = self.real_name
        
        return dct
    
    def can_be_updated(self):
        return self.id != -1

class Group(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "name": "",
        "description": "",
        "is_bug_group": False,
        "user_regexp": "",
        "is_active": False,
        "membership": []
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Group.ATTRIBUTES)
    
    def add_json(self, id_only = False):
        dct = {}
        for field in ("name", "description", "user_regexp", "is_active"):
            dct[field] = self[field]
        
        return dct
    
    def can_be_added(self):
        return bool(self.name and self.description)
    
    def update_json(self, id_only = False):
        dct = {}
        for field in ("name", "description", "user_regexp", "is_active"):
            dct[field] = self[field]
        
        return dct
    
    def can_be_updated(self):
        return self.id != -1

class Search(BugzillaObject):
    ATTRIBUTES = {
        "id": -1,
        "name": "",
        "query": ""
    }
    
    def __init__(self, attributes = {}):
        BugzillaObject.__init__(self, attributes)
        self.set_default_attributes(Search.ATTRIBUTES)
