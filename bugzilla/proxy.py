from .objects import *

"""
The base-class for lazy-loading objects. Its behaviour is the same as a normal
bugzilla-object, until an unknown attribute is accessed. In that case the complete
object is loaded from bugzilla (that method has to be implemented by subclasses)
and the lazy objects extends it attributes by the loaded objects attributes.
After that it converts to the loaded objects class.
Exceptions can be thrown when accessing attributes that have to be loaded from
bugzilla. Because of that, and because loading can be time-intensive, loading
can be disabled or only activated on certain attributes. The method triggers_loading
returns True if accessing the missing attribute should trigger loading. By default
this method returns True.
The loading process consists of 3 steps, loading, updating and cleaning. At first
the complete object is loaded from bugzilla. It has to be an instance of the
class passed to the constructor, otherwise an exception will be raised. After
that the lazy-object updates its values with the objects values and converts
itself to the objects class (please do not use this feature for religious
purposes). At last the _clean-method is used to get rid of class-specific
attributes.
"""
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
        if key not in self and self.load_on_missing_key and self.triggers_loading(key):
            self.load()
            
            return self[key]
        else:
            return BugzillaObject.__getitem__(self, key)
    
    def load(self):
        obj = self._load_object()
        if not isinstance(obj, self.real_class):
            raise ValueError()
        
        self.update(obj)
        object.__setattr__(self, "__class__", type(obj)) # wololol
        
        self._clean()
    
    def _clean(self):
        del self["loader"]
        del self["real_class"]
        del self["load_on_missing_key"]
    
    def _load_object(self):
        raise NotImplementedError("Subclasses have to implemented this method")
    
    def triggers_loading(self, attr):
        return True

class LazyUser(LazyBugzillaObject):
    def __init__(self, bugzilla, name):
        LazyBugzillaObject.__init__(self, bugzilla, User, {"name": name})
    
    def _load_object(self):
        return self.get_loader().get_user(self.name)
