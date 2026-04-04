from enum import Enum

from mime_processor import fuzzy_match_mimetype_category
from taggers.time_tagger import tag_time_tokens


class SpanClass(Enum):
    TARGET = "TARGET"
    CONSTRAINT = "CONSTRAINT"
    DESTINATION = "DESTINATION"
    ARGUMENT = "ARGUMENT"


class TokenClass(Enum):
    GLOB = "GLOB"
    FILEPATH = "FILEPATH"
    MIME = "MIME"
    NUMBER = "NUMBER"
    QUANTITY = "QUANTITY"
    ALIAS = "ALIAS"
    TIME = "TIME"
    ENUM = "ENUM"
    LITERAL = "LITERAL"
    GRAMMAR = "GRAMMAR"


# for filepath -> filepath preprocessor
# for mime -> table lookup
# number -> hard check
# quantity -> if follows a number
# alias -> check dictionary
# time -> time words
# enum -> check enum dictionary
# grammar -> spaCY


def token_loop(span: str):
    for token in span.split():
        print(token)
        token_class: TokenClass | None = None

        mime_result = fuzzy_match_mimetype_category(token)

        if mime_result is not None:
            token_class = TokenClass.MIME

        # check specific extension

        print(token_class)


# Have some ml model determine whether its the main thing or just a modifier for the main thing
#


def main():
    span = input("Enter span: ")

    # query wide preprocessors
    #
    tag_time_result = tag_time_tokens(span)
    time_phrases: list[str] = []
    continue_time_phrase: bool = False
    for token in tag_time_result:
        if token.label is not None:
            if continue_time_phrase:
                time_phrases[-1] = time_phrases[-1] + " " + token.text
            else:
                time_phrases.append(token.text)

            continue_time_phrase = True
        else:
            continue_time_phrase = False

    print("Time phrases:", time_phrases)
    token_loop(span)


if __name__ == "__main__":
    main()
