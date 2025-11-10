from enum import Enum

class SuffixEnum(str, Enum):
    METADATA        = "meta"
    CONVERSATION    = "conversation"
    PREFS           = "prefs"


class StorageType(str, Enum):
    STRING = "string"
    HASH   = "hash"
    JSON   = "json"
    LIST   = "list"