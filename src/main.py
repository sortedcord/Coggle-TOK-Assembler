from enum import Enum

from taggers.mime_tagger import fuzzy_match_mimetype_category
from taggers.path_tagger import tag_path_tokens
from taggers.time_tagger import tag_time_tokens

from enums import TokenClass


class SpanClass(Enum):
    TARGET = "TARGET"
    CONSTRAINT = "CONSTRAINT"
    DESTINATION = "DESTINATION"
    ARGUMENT = "ARGUMENT"


# for filepath -> filepath preprocessor
# for mime -> table lookup
# number -> hard check
# quantity -> if follows a number
# alias -> check dictionary
# time -> time words
# enum -> check enum dictionary
# grammar -> spaCY


def token_loop(span_list: list[tuple[str, TokenClass]]) -> list[tuple[str, TokenClass]]:
    res_span_list: list[tuple[str, TokenClass]] = []
    for token, class_ in span_list:
        if class_ is not TokenClass.LITERAL:
            res_span_list.append((token, TokenClass.TIME))
            continue

        mime_result = fuzzy_match_mimetype_category(token)

        if mime_result is not None:
            res_span_list.append((token, TokenClass.MIME))
        else:
            res_span_list.append((token, TokenClass.LITERAL))

    return res_span_list


# Have some ml model determine whether its the main thing or just a modifier for the main thing
#


def main():
    # query = "get all video and audio files from last week and delete them"
    query = "copy videos modified in the last 2 years and 18th january 1997 into backup folder"

    # query wide preprocessors
    #
    tag_time_result = tag_time_tokens(query)
    tag_path_result = tag_path_tokens(query)
    for token in tag_path_result:
        if token.label is not None:
            print(f"path -> {token.text} ({token.confidence})")
    time_phrase: str = ""
    continue_time_phrase: bool = False
    span_list = []
    for token in tag_time_result:
        if token.label is not None:
            if continue_time_phrase:
                time_phrase = time_phrase + " " + token.text
            else:
                time_phrase = token.text

            continue_time_phrase = True
        else:
            if time_phrase != "":
                span_list.append((time_phrase, TokenClass.TIME))
                time_phrase = ""

            span_list.append((token.text, TokenClass.LITERAL))
            continue_time_phrase = False

    span_list = token_loop(span_list)

    for token in span_list:
        print(f"{token[0]} - {token[1]}")


if __name__ == "__main__":
    main()
