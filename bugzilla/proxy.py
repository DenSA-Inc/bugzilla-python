from .objects import *

class LazyBugzillaObject(BugzillaObject):
    def __init__(self, loader, real_class, attributes):
        BugzillaObject.__init__(self, attributes)
        self.loader = loader
        self.real_class = real_class
        self.load_on_missing_key = True
    
    def get_load(self):
        return self.load_on_missing_key
    
    def set_load(self, load):
        self.load_on_missing_key = load
    
    def get_loader(self):
        return self.loader
    
    def set_loader(self, loader):
        self.loader = loader
    
    def __getitem__(self, key):
        if key not in self and self.load_on_missing_key:
            obj = self._load_object()
            if not isinstance(obj, self.real_class):
                raise ValueError()
            
            self.update(obj)
            object.__setattr__(self, "__class__", self.real_class) # wololol
            
            del self["loader"]
            del self["real_class"]
            del self["load_on_missing_key"]
            
            return self[key]
        else:
            return BugzillaObject.__getitem__(self, key)
    
    def _load_object(self):
        raise NotImplementedError("Subclasses have to implemented this method")

class LazyUser(LazyBugzillaObject):
    def __init__(self, bugzilla, name):
        LazyBugzillaObject.__init__(self, bugzilla, User, {"name": name})
    
    def _load_object(self):
        return self.get_loader().get_user(self.name)
