# Bugzilla4Python
This project aims to be a bugzilla-interface for python 3. The python-libraries that exist for bugzilla either use the old XMLRPC-interface or have a limited set of features or both. The best library I found was [https://github.com/gdestuynder/simple_bugzilla](https://github.com/gdestuynder/simple_bugzilla).

Despite the features of that library (which you should use if you don't like mine) I find several things missing. Some of these are that every bugzilla-object is of the same class and that only a subset of API-calls is supported. My answer to the big question "work with the existing code or rewrite from scratch" was "rewrite", so this project was created.

## How to use
A connection to bugzilla is provided through the Bugzilla-object.  

    import bugzilla
    b = bugzilla.Bugzilla(bugzilla_url, api_key)

The url is the "urlbase" of your bugzilla-installation, e.g. "https://bugzilla.mozilla.org/". The "/rest"-part is added automatically. If you want to use an api_key you can specify it as second argument.  
Other methods of login will not be supported as they are deprecated.

    a = bugzilla.Attachment()
    a["data"] = b"Hello World"
    a.content_type = "text/plain"
    a.update({
        "summary": "A summary",
        "file_name": "hello.txt"
    })
    b.add_attachment(a, bug_id, comment = "no comment")

Here an attachment is created and all three ways to set fields are shown. All bugzilla-objects derive from dict, so they can be treated as such. The second way is simply setting the attribute. Internally `a.x = value` will be converted to `a["x"] = value`. To update several fields at once, the `dict.update`-method can be used.  
In the end the attachment is added to a bug. Some API-calls accept more parameters than what belong to the object. Therefore the comment-field is passed to the method.

## Are there bugs?
Yes. I just don't see them because they are out of my line of sight. I tested the methods (roughly) in python 3.4 with an bugzilla-5.0-installation, I expect multiple bugs once this code will be used. If you find bugs send them to me for extermination or kill them yourselves.

## TODO's
I plan to add more features to this code, when this will happen is unknown. These features include:

 * Supporting all (not deprecated) API-methods
 * A good documentation. While the link to the documentation is given for every method every method should get a complete documentation of all possible parameters.
 * Lazy-fetching objects. Some API-calls return a object with only a subsets of it attributes (e.g. only an users email). An example would be an user-object which only knows its email. If any other attribute is accessed the object loads its attributes.
