from enum import Enum


class TokenClass(Enum):
    GLOB = "GLOB"
    FILEPATH = "FILEPATH"
    MIME = "MIME"
    NUMBER = "NUMBER"
    QUANTITY = "QUANTITY"
    ALIAS = "ALIAS"
    TIME = "TIME"
    ENUM = "ENUM"
    LITERAL = "LITERAL"  # >> Fallback
    GRAMMAR = "GRAMMAR"
