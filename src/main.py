from dataclasses import dataclass
from enums import TokenClass
from taggers.mime_tagger import tag_mime_tokens
from taggers.path_tagger import tag_path_tokens
from taggers.time_tagger import tag_time_tokens


@dataclass
class UnifiedToken:
    text: str
    token_class: TokenClass
    confidence: float = 1.0


class TokenAssembler:
    def __init__(self, query: str):
        self.query = query
        self.raw_tokens = query.split()

    def get_unified_spans(self) -> list[UnifiedToken]:
        """
        Runs all taggers and merges overlapping or adjacent tokens
        of the same class into single spans.
        """
        time_tags = tag_time_tokens(self.query)
        path_tags = tag_path_tokens(self.query)
        mime_tags = tag_mime_tokens(self.query)

        # 2. Map indices to classifications
        # We prioritize: PATH > TIME > MIME > LITERAL
        # Other taggers:
        ## number -> hard check
        # quantity -> if follows a number
        # alias -> check dictionary
        # time -> time words
        # enum -> check enum dictionary
        # grammar -> spaCY

        classifications: list[UnifiedToken] = []

        # zip based on the word token index
        for i in range(len(self.raw_tokens)):
            text = self.raw_tokens[i]

            if path_tags[i].label:
                classifications.append(
                    UnifiedToken(
                        text, TokenClass.FILEPATH, path_tags[i].confidence or 1.0
                    )
                )
            elif time_tags[i].label:
                classifications.append(UnifiedToken(text, TokenClass.TIME))
            elif mime_tags[i].label:
                classifications.append(UnifiedToken(text, TokenClass.MIME))
            else:
                classifications.append(UnifiedToken(text, TokenClass.LITERAL))

        return self._merge_adjacent(classifications)

    def _merge_adjacent(self, tokens: list[UnifiedToken]) -> list[UnifiedToken]:
        if not tokens:
            return []

        merged = []
        current = tokens[0]

        for next_token in tokens[1:]:
            # merge if they share a class and aren't Literals
            if (
                next_token.token_class == current.token_class
                and current.token_class != TokenClass.LITERAL
            ):
                current.text += f" {next_token.text}"
                # keep the highest confidence in the span
                current.confidence = max(current.confidence, next_token.confidence)
            else:
                merged.append(current)
                current = next_token

        merged.append(current)
        return merged


def process_query(query: str):
    assembler = TokenAssembler(query)
    spans = assembler.get_unified_spans()

    print(f"\nQuery: {query}")
    print("-" * 30)

    for span in spans:
        conf_str = (
            f" ({span.confidence:.2f})"
            if span.token_class != TokenClass.LITERAL
            else ""
        )
        print(f"[{span.token_class.value: <10}] {span.text}{conf_str}")


def main():
    queries = [
        "copy videos modified in the last 2 years and 18th january 1997 into backup folder",
        "find all python files in ~/projects/coggle created yesterday",
        "split video.mkv into 10 minute segments as hello_1.mkv and hello_2.mkv",
    ]

    for q in queries:
        process_query(q)


if __name__ == "__main__":
    main()
