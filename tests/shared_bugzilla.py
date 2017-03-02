from bugzilla import Bugzilla
from os import path

CREDENTIALS_FILE = "bugzilla-credentials"
CREDENTIALS_FILE_ALT = "bugzilla-credentials.txt"

if not path.isfile(CREDENTIALS_FILE) and not path.isfile(CREDENTIALS_FILE_ALT):
    raise ValueError("Neither a file %s nor %s with bugzilla-credentials exists" %
                        (CREDENTIALS_FILE, CREDENTIALS_FILE_ALT))

file_name = CREDENTIALS_FILE if path.isfile(CREDENTIALS_FILE) else CREDENTIALS_FILE_ALT
with open(file_name) as file:
    url = file.readline().rstrip()
    api_key = file.readline().rstrip()
    if not api_key: api_key = None # there was no second line in the file

bugzilla = Bugzilla(url, api_key)
b = buggy = zilla = bugzilla # variable aliases for better use
