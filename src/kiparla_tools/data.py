import collections
import functools
import csv # for annotators' statistics
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import logging

import regex as re
import pandas as pd
import networkx as nx

import kiparla_tools.process_text as pt
import kiparla_tools.dataflags as df
import kiparla_tools.utils as utils
from kiparla_tools.logging_utils import setup_logging

logger = logging.getLogger(__name__)
setup_logging(logger)

@dataclass
class Token:
    text: str
    id: str
    span: Tuple[int,int] = (0,0)
    token_type: df.tokentype = df.tokentype.linguistic
    orig_text: str = ""
    unknown: bool = False
    intonation_pattern: df.intonation = df.intonation.plain
    position_in_tu: df.position = df.position.inner
    volume: df.volume = None
    overlaps: Dict[int, Tuple[int, int]] = field(default_factory=lambda: {})
    slow_pace: Dict[int, Tuple[int, int]] = field(default_factory=lambda: {})
    guesses: Dict[int, Tuple[int, int]] = field(default_factory=lambda: {})
    fast_pace: Dict[int, Tuple[int, int]] = field(default_factory=lambda: {})
    low_volume: Dict[int, Tuple[int, int]] = field(default_factory=lambda: {})
    interruption: bool = False
    truncation: bool = False
    prosodiclink: bool = False
    spaceafter: bool = True
    non_ita: bool = False
    iso_code: str = "ita"
    non_ortho: bool = False
    prolongations: Dict[int, int] = field(default_factory=lambda: {})
    warnings: Dict[str, int] = field(default_factory=lambda: collections.defaultdict(int))
    errors: List[str] = field(default_factory=lambda: collections.defaultdict(int))

    def __post_init__(self):

        self.orig_text = self.text

        if len(self.text.strip()) == 0:
            return

        chars = ["[","]", "(", ")", "<", ">", "°"]

        for char in chars:
            self.text = self.text.replace(char, "")

        if all(c == "x" for c in self.text):
            self.token_type = df.tokentype.unknown
            self.text = "x"
            return

        if self.text[0] == "$":
            logger.debug("Not existing in italian detected in token %s", self.text)
            self.non_ortho = True
            self.text = self.text[1:]

        if self.text[0] == "#":
            logger.debug("Different language detected in token %s", self.text)
            self.non_ita = True
            self.iso_code = "NO_ISO_CODE"
            self.text = self.text[1:]


        # ! STEP 1: check that token has shape '?([a-z]+:*)+[-']?[.,?]
        matching_po = re.fullmatch(r"po':*[.,?]?", self.text)
        matching_anonymized = self.text.startswith("@")
        matching_instance = re.fullmatch(r"['~-]?(\p{L}+:*)*\p{L}+:*[-'~]?[.,?]?", self.text)

        if matching_anonymized:
            self.token_type = df.tokentype.anonymized
            return

        if matching_instance is None:
            if self.text == "{P}":
                self.token_type = df.tokentype.shortpause
                return
            elif self.text.startswith("{"):
                self.token_type = df.tokentype.nonverbalbehavior
                return
            elif matching_po is None:
                self.token_type = df.tokentype.error
                return

        if matching_po:
            self.text, _ = re.subn(r"'(:*)",
                                    r"\1'",
                                    self.text)

        # ! STEP2: find final prosodic features: intonation, truncation and interruptions
        if self.text.endswith("."):
            self.intonation_pattern = df.intonation.falling
            self.text = self.text[:-1] # this line removes the last character of the string (".")
        elif self.text.endswith(","):
            self.intonation_pattern = df.intonation.weakly_rising
            self.text = self.text[:-1]
        elif self.text.endswith("?"):
            self.intonation_pattern = df.intonation.rising
            self.text = self.text[:-1]
        elif self.text.endswith("-") or self.text.endswith("~"):
            self.interruption = True
        elif self.text.startswith("-") or self.text.startswith("~"):
            self.interruption = True
        elif self.text.endswith("'") or self.text.startswith("'"):
            alpha_text = [x for x in self.text if x.isalpha()]
            if "".join(alpha_text) not in ["po"]:
                self.truncation = True

        # ! STEP3: at this point we should be left with the bare word with only prolongations
        logger.debug("Token after step 2: %s", self.text)

        tmp_text = []
        i=0
        for char in self.text:
            if char in [":"]:
                tmp_text.append((-2, char))
            elif char in ["'", "-", "~"]:
                tmp_text.append((-2, char))
                i+=1
            else:
                tmp_text.append((i, char))
                i+=1

        matches = list(re.finditer(r":+", self.text))
        for match in matches:
            begin, end = match.span()
            char_id = begin
            while tmp_text[char_id][0]<0:
                char_id -= 1
            char_id = tmp_text[char_id][0]
            span_len = end-begin
            self.prolongations[char_id] = span_len

        new_text, substitutions = re.subn(r":+", "", self.text)
        if substitutions > 0:
            self.text = new_text

        # check for high volume
        if any(letter.isupper() for letter in self.text):
            self.volume = df.volume.high
        self.text = self.text.lower()

    def add_span(self, start, end):
        self.span = (start, end)

    def update_span(self, end):
        self.span = (self.span[0], end)

    def __str__(self):
        return self.text

    def add_info(self, field_name, field_value):
        if field_name == "ProsodicLink":
            self.prosodiclink = True

        if field_name == "overlaps":
            match_id, id_from, id_to = field_value
            self.overlaps[match_id] = (id_from, id_to)

        if field_name == "slow_pace":
            span_id, id_from, id_to = field_value
            self.slow_pace[span_id] = (id_from, id_to)

        if field_name == "fast_pace":
            span_id, id_from, id_to = field_value
            self.fast_pace[span_id] = (id_from, id_to)

        if field_name == "low_volume":
            span_id, id_from, id_to = field_value
            self.low_volume[span_id] = (id_from, id_to)
            self.volume = df.volume.low

        if field_name == "guesses":
            span_id, id_from, id_to = field_value
            self.guesses[span_id] = (id_from, id_to)

        if field_name == "SpaceAfter":
            self.spaceafter = False
            if self.truncation:
                self.truncation = False

        if field_name == "Language":
            self.non_ita = True
            self.iso_code = field_value



@dataclass
class TranscriptionUnit:
    tu_id : int
    speaker: str
    start: float
    end: float
    duration: float
    annotation: str
    orig_annotation: str = ""
    include: bool = True
    non_ita: df.languagevariation = df.languagevariation.none
    overlapping_spans: List[Tuple[int, int]] = field(default_factory=lambda: [])
    overlapping_times: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {})
    nvb_in_overlap: Dict[str, bool] = field(default_factory=lambda: {})
    overlapping_matches: Dict[Tuple[int, int], str] = field(default_factory=lambda: [])
    overlap_duration: Dict[str, float] = field(default_factory=lambda: {})

    low_volume_spans: List[Tuple[int, int]] = field(default_factory=lambda: [])
    high_volume_spans: List[Tuple[int, int]] = field(default_factory=lambda: [])
    guessing_spans: List[Tuple[int, int]] = field(default_factory=lambda: [])
    fast_pace_spans: List[Tuple[int, int]] = field(default_factory=lambda: [])
    slow_pace_spans: List[Tuple[int, int]] = field(default_factory=lambda: [])

    warnings: Dict[str, int] = field(default_factory=lambda: collections.defaultdict(int))
    errors: List[str] = field(default_factory=lambda: collections.defaultdict(bool))
    parentheses: List[Tuple[int, str]] = field(default_factory=lambda: [])
    splits: List[int] = field(default_factory=lambda: [])
    tokens: Dict[int, Token] = field(default_factory=lambda: {})
    ntokens: int = 0

    def __post_init__(self):
        self.orig_annotation = self.annotation

        if self.annotation is None or len(self.annotation)<1:
            logger.info("Empty annotation for TU %s", self.tu_id)
            self.include = False
            return

        self.annotation = self.annotation.strip()

        if self.annotation[:2] == "# ":
            # print(self.annotation)
            logger.debug("Different language detected in TU %s", self.tu_id)
            logger.debug("%s >> %s", self.annotation, self.annotation[1:])
            self.non_ita = df.languagevariation.some
            self.annotation = self.annotation[1:].strip()
            # print(self.annotation)
            # input()

        if self.annotation[:2] == "#_":
            logger.debug("Different language detected in TU %s", self.tu_id)
            logger.debug("%s >> %s", self.annotation, self.annotation[1:])
            self.non_ita = df.languagevariation.all
            self.annotation = self.annotation[2:].strip()
            return


        warning_functions_to_apply = [
            ("SYMBOL_NOT_ALLOWED", pt.clean_non_jefferson_symbols),   # remove non jefferson symbols
            ("META_TAGS", pt.meta_tag),                               # transform metalinguistic annotations and shortpauses
            ("UNEVEN_SPACES", pt.check_spaces),                       # remove spaces before and after parentheses
            ("TRIM_PAUSES", pt.remove_pauses),                        # remove leading and trailing shortpauses
            ("TRIM_PROSODICLINKS", pt.remove_prosodiclinks),          # remove leading and trailing prosodiclinks
            ("UNEVEN_SPACES", pt.space_prosodiclink),                 # remove space before or after prosodiclinks
            ("OVERLAP_PROLONGATION", pt.overlap_prolongations),       # fix \w+:*[:
            ("MULTIPLE_SPACES", pt.remove_spaces),                    # remove double spaces
            ("ACCENTS", pt.replace_che),                              # replace chè with ché
            ("ACCENTS", pt.replace_po),                               # replace pò with po'
            ("ACCENTS", pt.replace_pero),                             # replace o'/e' with ò/è
            ("NUMBERS", pt.check_numbers),                            # replace numbers with letters
        ]

        error_functions_to_apply = [
            ("UNBALANCED_DOTS", pt.check_even_dots),                    # check if dots are balanced
            ("UNBALANCED_PACE", pt.check_angular_parentheses),          # check if angular parentheses are balanced
            ("UNBALANCED_GUESS", functools.partial(pt.check_normal_parentheses,
                                                open_char="(", close_char=")")),    # check if guessing parentheses are balanced
            ("UNBALANCED_OVERLAP", functools.partial(pt.check_normal_parentheses,
                                                open_char="[", close_char="]")),    # check if overlapping parentheses are balanced
        ]

        for warning_label, warning_function in warning_functions_to_apply:
            substitutions, new_transcription = warning_function(self.annotation)
            if substitutions > 0:
                logger.debug("Applied %d substitution(s) with function %s", substitutions, warning_function.__name__)
                logger.debug("%s >> %s", self.annotation, new_transcription)
            self.warnings[warning_label] += substitutions
            self.annotation = new_transcription

        for error_label, error_function in error_functions_to_apply:
            self.errors[error_label] = not error_function(self.annotation)
            if self.errors[error_label]:
                function_name = getattr(error_function, "func", error_function).__name__
                logger.debug("Function %s produced error", function_name)

        # fix spaces before and after dots
        if "°" in self.annotation and not self.errors["UNBALANCED_DOTS"]:
            substitutions, new_transcription = pt.check_spaces_dots(self.annotation)
            if substitutions > 0:
                logger.debug("Applying %d substitutions with function check_spaces_dots", substitutions)
                logger.debug("%s >> %s", self.annotation, new_transcription)
            self.warnings["UNEVEN_SPACES"] += substitutions
            self.annotation = new_transcription

        # fix spaces before and after angular
        if "<" in self.annotation and not self.errors["UNBALANCED_PACE"]:
            substitutions, new_transcription = pt.check_spaces_angular(self.annotation)
            if substitutions > 0:
                logger.debug("Applying %d substitutions with function check_spaces_angular", substitutions)
                logger.debug("%s >> %s", self.annotation, new_transcription)
            self.warnings["UNEVEN_SPACES"] += substitutions
            self.annotation = new_transcription

        # check how many varying pace spans have been transcribed
        if "<" in self.annotation and not self.errors["UNBALANCED_PACE"]:
            matches_left, matches_right = pt.matches_angular(self.annotation)
            self.slow_pace_spans = [x[1] for x in matches_left]
            self.fast_pace_spans = [x[1] for x in matches_right]

            if len(self.slow_pace_spans) + len(self.fast_pace_spans) > 0:
                logger.debug("Found %d varying pace spans", len(self.slow_pace_spans) + len(self.fast_pace_spans))

        # check how many low volume spans have been transcribed
        if "°" in self.annotation and not self.errors["UNBALANCED_DOTS"]:
            matches = list(re.finditer(r"°[^°]+°", self.annotation))
            if len(matches)>0:
                self.low_volume_spans = [match.span() for match in matches]
                logger.debug("Found %d low volume spans", len(self.low_volume_spans))

        # check how many high volume spans have been transcribed
        matches = list(re.finditer(r"\b[A-ZÀÈÉÌÒÓÙ]+(?:\s+[A-ZÀÈÉÌÒÓÙ]+)*\b", self.annotation))
        if matches:
            self.high_volume_spans = [match.span() for match in matches]
            logger.debug("Found %d high volume spans", len(self.high_volume_spans))

        # check how many overlapping spans have been transcribed
        if "[" in self.annotation and not self.errors["UNBALANCED_OVERLAP"]:
            matches = list(re.finditer(r"\[[^\]]+\]", self.annotation))
            if len(matches)>0:
                self.overlapping_spans = [match.span() for match in matches]
                logger.debug("Found %d overlapping spans", len(self.overlapping_spans))

        # check how many guessing spans have been transcribed
        if "(" in self.annotation and not self.errors["UNBALANCED_GUESS"]:
            matches = list(re.finditer(r"\([^)]+\)", self.annotation))
            if len(matches)>0:
                self.guessing_spans = [match.span() for match in matches]
                logger.debug("Found %d guessing spans", len(self.guessing_spans))

        # invert [.,?][:-~]
        substitutions, new_transcription = pt.switch_symbols(self.annotation)
        if substitutions > 0:
            logger.debug("Applied %d substitution(s) with function switch_symbols", substitutions)
            logger.debug("%s >> %s", self.annotation, new_transcription)
        self.warnings["SWITCHES"] += substitutions
        self.annotation = new_transcription

        # invert NVB and parentheses
        substitutions, new_transcription = pt.switch_NVB(self.annotation)
        if substitutions > 0:
            logger.debug("Applied %d substitution(s) with function switch_NVB", substitutions)
            logger.debug("%s >> %s", self.annotation, new_transcription)
        self.warnings["SWITCHES"] += substitutions
        self.annotation = new_transcription

        # remove unit if it only includes non-alphabetic symbols or is empty
        if all(c in ["[", "]", "(", ")", "°", ">", "<", "-", "'", "#"] for c in self.annotation):
            logger.info("Removing TU %s", self.tu_id)
            self.include = False
            return

    def tokenize(self):

        if not self.include:
            return

        logger.debug("Tokenizing TU %s", self.tu_id)

        # ! split on space and prosodic links
        tokens = re.split(r"( |=)", self.annotation)
        logger.debug("%s >> %s", self.annotation, tokens)


        start_pos = 0
        end_pos = 0
        token_id = -1

        for tok in tokens:
            logger.debug("Extracting token '%s'", tok)

            if len(tok) == 0:
                logger.error("Empty token")
                logger.error("TU %s, tokens %s", self.tu_id, tokens)
            end_pos = start_pos + len(tok)
            logger.debug("Start: %d, End: %d, %s", start_pos, end_pos, self.annotation[start_pos:end_pos])

            if tok == " ":
                logger.debug("Skipping space")
                start_pos = end_pos
                continue

            if tok == "=":
                logger.debug("Adding prosodic link to token %s", self.tokens[token_id].text)
                self.tokens[token_id].add_info("ProsodicLink", "Yes")

            elif "'" in tok:
                apostrophe_idx = tok.index("'")
                prefix = tok[:apostrophe_idx]
                suffix = tok[apostrophe_idx+1:]

                letter_in_prefix = any(c.isalpha() for c in prefix)
                letter_in_suffix = any(c.isalpha() for c in suffix)

                logger.debug("Found apostrophe. Prefix: %s, Suffix: %s", prefix, suffix)

                if letter_in_suffix and letter_in_prefix:
                    subtoken1 = tok[:apostrophe_idx+1]
                    subtoken2 = tok[apostrophe_idx+1:]

                    start1 = start_pos
                    end1 = start1 + len(subtoken1)
                    start2 = end1
                    end2 = end_pos

                    token_id += 1
                    new_token = Token(subtoken1, f"{self.tu_id}-{token_id}")
                    logger.debug("Adding token %s", new_token)
                    new_token.add_span(start1, end1)
                    new_token.add_info("SpaceAfter", "No")
                    logger.debug("Adding spaceafter feature")
                    self.tokens[token_id] = new_token

                    token_id += 1
                    new_token = Token(subtoken2, f"{self.tu_id}-{token_id}")
                    logger.debug("Adding token %s", new_token)
                    new_token.add_span(start2, end2)
                    self.tokens[token_id] = new_token

                else:
                    token_id += 1
                    new_token = Token(tok, f"{self.tu_id}-{token_id}")
                    logger.debug("Adding token %s", new_token)
                    new_token.add_span(start_pos, end_pos)
                    self.tokens[token_id] = new_token

            else:
                token_id += 1
                new_token = Token(tok, f"{self.tu_id}-{token_id}")
                logger.debug("Adding token %s", new_token)
                new_token.add_span(start_pos, end_pos)
                self.tokens[token_id] = new_token

            start_pos = end_pos

        if df.languagevariation.all in self.non_ita:
            logger.debug("Adding dialectal variation to all tokens in TU")
            for _, tok in self.tokens.items():
                tok.token_type=df.tokentype.linguistic
                tok.add_info("Language", "NO_ISO_CODE")

        all_variation = True
        some_variation = False
        for _, tok in self.tokens.items():

            if tok.non_ita:
                some_variation = True
            else:
                all_variation = False

        if some_variation:
            self.non_ita = df.languagevariation.some
        if all_variation:
            self.non_ita = df.languagevariation.all


    def add_token_features(self):

        ids = []
        token_ids = []

        for tok_id, tok in self.tokens.items():
            i=0
            for char in tok.orig_text:
                if char in [":", ".", ",", "?"]:
                    ids.append(-1)
                    token_ids.append(-1)
                elif char in ["[", "]", "(", ")", ">", "<", "°"]:
                    ids.append(-2)
                    token_ids.append(-2)
                else:
                    ids.append(i)
                    token_ids.append(tok_id)
                    i+=1

            ids.append(-3)
            token_ids.append(-3)

        for feature_name, spans in [("slow_pace", self.slow_pace_spans),
                                    ("fast_pace", self.fast_pace_spans),
                                    ("low_volume", self.low_volume_spans),
                                    ("high_volume", self.high_volume_spans),
                                    ("guesses", self.guessing_spans)]:

            for span_id, span in enumerate(spans):
                a, b = span[0], span[1]

                data = list(zip(token_ids[a:b], ids[a:b]))
                unique_tokens = set(x for x,y in data if x > -1)

                char_ranges = {x:[] for x in unique_tokens}
                for token_id, pos_id in data:
                    if token_id in char_ranges:
                        char_ranges[token_id].append(pos_id)

                for idx in char_ranges:
                    char_ranges[idx] = (min(char_ranges[idx]), max(char_ranges[idx])+1)
                    self.tokens[idx].add_info(feature_name, (span_id,
                                                            char_ranges[idx][0],
                                                            char_ranges[idx][1]))


        if len(self.overlapping_matches) > 0:

            # TODO: handle overlaps only on prolongations
            for span, match_id in self.overlapping_matches.items():
                a, b = span[0], span[1]

                data = list(zip(token_ids[a:b], ids[a:b]))
                unique_tokens = set(x for x,y in data if x > -1)

                char_ranges = {x:[] for x in unique_tokens}
                for token_id, pos_id in data:
                    if token_id in char_ranges:
                        char_ranges[token_id].append(pos_id)

                for id in char_ranges:
                    char_ranges[id] = (min(char_ranges[id]), max(char_ranges[id])+1)
                    self.tokens[id].add_info("overlaps", (match_id,
                                                        char_ranges[id][0],
                                                        char_ranges[id][1]))

        # add position of token in TU
        if len(self.tokens) > 0:
            first_token, last_token = self.tokens[0], self.tokens[max(self.tokens.keys())]
            first_token.position_in_tu = first_token.position_in_tu | df.position.start
            last_token.position_in_tu = last_token.position_in_tu | df.position.end


@dataclass
class Transcript:
    tr_id: str
    speakers: Dict[str, int] = field(default_factory=lambda: {})
    tiers: Dict[str, bool] = field(default_factory=lambda: collections.defaultdict(bool))
    last_speaker_id: int = 0
    transcription_units_dict: Dict[str, TranscriptionUnit] = field(default_factory=lambda: collections.defaultdict(list))
    transcription_units: List[TranscriptionUnit] = field(default_factory=lambda: [])
    tot_length: float = 0
    # turns: List[Turn] = field(default_factory=lambda: [])
    time_based_overlaps: nx.Graph = field(default_factory=lambda: nx.Graph())
    statistics: pd.DataFrame = None
    overlap_events: Dict[int, Tuple[float, float, int]] = field(default_factory=lambda: {})

    def add(self, tu:TranscriptionUnit):

        if not tu.speaker in self.speakers:
            self.speakers[tu.speaker] = 0
        if tu.include:
            self.speakers[tu.speaker] += 1
        self.transcription_units_dict[tu.tu_id] = tu

    def sort(self):
        self.transcription_units = sorted(self.transcription_units_dict.items(), key=lambda x: x[1].start)
        self.transcription_units = [y for x, y in self.transcription_units]
        self.tot_length = self.transcription_units[-1].end

    def purge_speakers(self):
        speakers_to_remove = []
        for speaker in self.speakers:
            if self.speakers[speaker] == 0:
                speakers_to_remove.append(speaker)

        for speaker in speakers_to_remove:
            logger.warning("Removing speaker %s", speaker)
            del self.speakers[speaker]

    def find_overlaps(self, duration_threshold=0):

        G = nx.Graph()

        for tu1 in self.transcription_units:
            for tu2 in self.transcription_units:
                if tu1.include and tu2.include and tu2.tu_id > tu1.tu_id:
                    if not tu1.tu_id in G.nodes:
                        G.add_node(tu1.tu_id, speaker = tu1.speaker, overlaps = tu1.overlapping_spans)

                    if not tu2.tu_id in G.nodes:
                        G.add_node(tu2.tu_id, speaker = tu2.speaker, overlaps = tu2.overlapping_spans)

                    # De Morgan on tu1.end <= tu2.start or tu2.end <= tu1.start
                    # the two units overlap in time
                    if tu1.end > tu2.start and tu2.end > tu1.start:
                        start = max(tu1.start, tu2.start)
                        end = min(tu1.end, tu2.end)
                        duration = min(tu1.end, tu2.end)-max(tu1.start, tu2.start)

                        G.add_edge(tu1.tu_id, tu2.tu_id,
                                    start = start,
                                    end = end,
                                    duration = duration,
                                    spans = {tu1.tu_id:None, tu2.tu_id:None})

        self.time_based_overlaps = G


    def check_overlaps(self, duration_threshold, relations_to_ignore = []):

        logger.debug("Graph at beginning: %s", self.time_based_overlaps.number_of_edges())

        to_remove = []
        for u, v in self.time_based_overlaps.edges():
            if all(df.tokentype.nonverbalbehavior in tok.token_type for _, tok in self.transcription_units_dict[u].tokens.items()) or \
            all(df.tokentype.nonverbalbehavior in tok.token_type for _, tok in self.transcription_units_dict[v].tokens.items()):
                to_remove.append((u, v))

        for u, v in to_remove:
            logger.warning("Removing edge %s-%s because of metalinguistic elements", u, v)
            self.time_based_overlaps.remove_edge(u, v)

        logger.debug("Graph after removing metalinguistic elements: %s", self.time_based_overlaps.number_of_edges())

        if len(relations_to_ignore) > 0:
            for u, v in relations_to_ignore:
                logger.warning("Removing edge %s-%s because of relations to ignore", u, v)
                if self.time_based_overlaps.has_edge(u, v):
                    self.time_based_overlaps.remove_edge(u, v)

        logger.debug("Graph after removing ignored elements: %s", self.time_based_overlaps.number_of_edges())

        # REMOVE OVERLAPPING IF OVERLAP_DURATION < DURATION THRESHOLD AND NO SPAN ANNOTATED
        for node in self.time_based_overlaps.nodes:
            to_remove = []

            for neigh_node in self.time_based_overlaps.neighbors(node):
                if self.time_based_overlaps[node][neigh_node]["duration"] < duration_threshold:
                    tu1 = self.transcription_units_dict[node]
                    tu2 = self.transcription_units_dict[neigh_node]
                    if len(tu1.overlapping_spans) + len(tu2.overlapping_spans) == 0:
                        min_tu, max_tu = sorted([tu1, tu2], key=lambda x: x.tu_id)
                        min_tu.end = min_tu.end - self.time_based_overlaps[node][neigh_node]["duration"]/2
                        max_tu.start = max_tu.start + self.time_based_overlaps[node][neigh_node]["duration"]/2

                        if min_tu.end <= min_tu.start:
                            logger.error("TU %s has end <= start, %.2f, %.2f", min_tu.tu_id, min_tu.end, min_tu.start)

                        if max_tu.end <= max_tu.start:
                            logger.error("TU %s has end <= start, %.2f, %.2f", max_tu.tu_id, max_tu.end, max_tu.start)


                        #TODO: check tu still exists!
                        tu1.warnings["MOVED_BOUNDARIES"] += 1
                        tu2.warnings["MOVED_BOUNDARIES"] += 1
                        to_remove.append((node, neigh_node))

            for u, v in to_remove:
                logger.warning("Removing edge %s-%s because overlap is %.2f and no edge is present", u, v, self.time_based_overlaps[u][v]["duration"])
                self.time_based_overlaps.remove_edge(u, v)

        logger.debug("Graph after removing spurious overlaps: %s", self.time_based_overlaps.number_of_edges())


        cliques = sorted(nx.find_cliques(self.time_based_overlaps), key=lambda x: len(x))
        cliques = list(filter(lambda x: len(x) > 1, cliques))

        self.overlap_events = {}
        logger.info("Found %d cliques", len(cliques))

        for clique_id, clique in enumerate(cliques):
            # if len(clique)>1:
            starts = []
            ends = []
            nvb_in_clique = False

            for node in clique:
                starts.append(self.transcription_units_dict[node].start)
                ends.append(self.transcription_units_dict[node].end)
                nvb_in_clique = nvb_in_clique or any(df.tokentype.nonverbalbehavior in tok.token_type for _, tok in self.transcription_units_dict[node].tokens.items())

            overlap_start = max(starts)
            overlap_end = min(ends)

            self.overlap_events[clique_id] = (overlap_start, overlap_end)


            for node in clique:
                clique_tup = tuple(x for x in clique if not x == node)
                self.transcription_units_dict[node].overlapping_times[clique_tup] = (overlap_start,
                                                                                    overlap_end,
                                                                                    clique_id,
                                                                                    nvb_in_clique)


        sorted_cliques = list(sorted(self.overlap_events.items(), key=lambda x: x[1][0]))
        # cliques_map = {}
        # i=1
        # for clique_id, clique in sorted_cliques:
        #     cliques_map[clique_id] = i
        #     i+=1

        for _, tu  in self.transcription_units_dict.items():
            spans = tu.overlapping_spans
            times = tu.overlapping_times

            if len(spans) == len(times):
                logger.debug("Overlaps are consistent for TU %s", tu.tu_id)

                sorted_overlaps = list(sorted(tu.overlapping_times.items(), key=lambda x: x[1][0]))
                # sorted_overlaps = ["+".join([str(el) for el in x]) for x, y in sorted_overlaps]
                sorted_overlaps = [x[2] for _, x in sorted_overlaps]
                tu.overlapping_matches = dict(zip(tu.overlapping_spans, sorted_overlaps))

            elif len(spans) == 0:
                logger.warning("TU %s has NO annotated spans and %d time overlaps", tu.tu_id, len(times))

                removables = []
                for el in tu.overlapping_times:
                    clique_id =  tu.overlapping_times[el][2]
                    nvb_in_overlap = tu.overlapping_times[el][3]
                    tu.overlap_duration["+".join([str(x) for x in el])] = tu.overlapping_times[el][1]-tu.overlapping_times[el][0]

                    if nvb_in_overlap or tu.overlapping_times[el][1]-tu.overlapping_times[el][0] < duration_threshold:
                        removables.append(el)

                    # if nvb_in_overlap:
                    #     logger.warning("Ignoring issue because of nonverbal behavior")
                    #     tu.warnings["MISMATCHING_OVERLAPS"] = True
                    # else:
                    #     tu.errors["OVERLAPS:MISSING_ANNOTATION"] = True

                if len(removables) == len(times):
                    logger.warning("Ignoring issue because of nonverbal behavior")
                    tu.warnings["MISMATCHING_OVERLAPS"] = True
                else:
                    tu.errors["OVERLAPS:MISSING_ANNOTATION"] = True


            elif len(times) == 0:
                logger.warning("TU %s has %d annotated spans and NO time overlaps", tu.tu_id, len(spans))
                tu.errors["OVERLAPS:MISSING_TIME"] = True

                sorted_overlaps = ["?" for el in tu.overlapping_spans]
                tu.overlapping_matches = dict(zip(tu.overlapping_spans, sorted_overlaps))

            elif len(times) > len(spans):

                difference = len(times) - len(spans)

                removables = []
                for el in tu.overlapping_times:
                    duration = tu.overlapping_times[el][1]-tu.overlapping_times[el][0]
                    nvb = tu.overlapping_times[el][3]

                    if duration<duration_threshold or nvb:
                        removables.append(el)

                if len(removables) == difference:
                    sorted_overlaps = list(sorted(tu.overlapping_times.items(), key=lambda x: x[1][0]))
                    # sorted_overlaps = ["+".join([str(el) for el in x]) for x, y in sorted_overlaps]
                    sorted_overlaps = [x[2] for _, x in sorted_overlaps if not x[2] in removables]
                    tu.overlapping_matches = dict(zip(tu.overlapping_spans, sorted_overlaps)) #TODO
                    tu.warnings["MISMATCHING_OVERLAPS"] = True

                else:
                    tu.errors["MISMATCHING_OVERLAPS"] = True
                    sorted_overlaps = ["?" for el in tu.overlapping_spans]
                    tu.overlapping_matches = dict(zip(tu.overlapping_spans, sorted_overlaps))

                    for el in tu.overlapping_times:
                        tu.overlap_duration["+".join([str(x) for x in el])] = tu.overlapping_times[el][1]-tu.overlapping_times[el][0]
            else:
                logger.warning("TU %s has %d annotated spans and %d time overlaps", tu.tu_id, len(spans), len(times))
                tu.errors["MISMATCHING_OVERLAPS"] = True

                sorted_overlaps = ["?" for el in tu.overlapping_spans]
                tu.overlapping_matches = dict(zip(tu.overlapping_spans, sorted_overlaps))

                for el in tu.overlapping_times:
                    tu.overlap_duration["+".join([str(x) for x in el])] = tu.overlapping_times[el][1]-tu.overlapping_times[el][0]

    # Statistic calculations
    def get_stats (self, annotators_data_csv="data/data_description.csv", split_size=60):

        stats = {}

        stats["num_speakers"] = len(self.speakers) # number of speakers

        # number of TUs
        stats["num_tu"] = utils.compute_stats_per_minute(self.transcription_units, split_size)

        # number of TUs excluding metalinguistic tokens
        stats["num_ling_tu"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                            lambda x: any(token.token_type & df.tokentype.linguistic for token in x.tokens.values()))
        # durata delle tus per minuto
        stats["tus_duration_per_minute"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                        f2_tu=lambda x: x.duration)
        # number of tokens per minute
        stats["tokens_per_minute"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                    f2_tu=lambda x: len(x.tokens))
        # number of linguistic tokens per minute
        stats["linguistic_tokens_min"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                        f2_tu=lambda x: sum(1 for token in x.tokens.values()
                                                                        if token.token_type == df.tokentype.linguistic))
        # number of metalinguistic tokens per minute
        stats["metalinguistic_tokens_min"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                        f2_tu=lambda x: sum(1 for token in x.tokens.values()
                                                                        if token.token_type == df.tokentype.nonverbalbehavior))
        # number of shortpauses per minute
        stats["shortpauses_min"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                f2_tu=lambda x: sum(1 for token in x.tokens.values()
                                                                if token.token_type == df.tokentype.shortpause))
        # number of errors per minute
        stats["errors_min"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                            f2_tu=lambda x: sum(1 for token in x.tokens.values()
                                                            if token.token_type == df.tokentype.error))
        # number of unknows tokens per minute
        stats["unknown_tokens_min"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                    f2_tu=lambda x: sum(1 for token in x.tokens.values()
                                                                    if token.token_type == df.tokentype.unknown))
        # average number of token/minute
        stats["avg_tokens_per_min"] = []
        for n_tokens, n_tus in zip(stats["tokens_per_minute"], stats["num_tu"]):
            if n_tus > 0:
                stats["avg_tokens_per_min"].append(n_tokens / n_tus)
            else:
                stats["avg_tokens_per_min"].append(0)

        # average duration of tus per minute
        stats["avg_duration_per_min"] = []
        for n_tokens, n_tus in zip(stats["tus_duration_per_minute"], stats["num_tu"]):
            if n_tus > 0:
                stats["avg_duration_per_min"].append(n_tokens / n_tus)
            else:
                stats["avg_duration_per_min"].append(0)

        # intonation pattern al minuto
        stats["intonation_patterns_min"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                        f2_tu=lambda x: sum(1 for token in x.tokens.values() if token.intonation_pattern != df.intonation.plain))
        # prolongations per minute
        stats["prolongations"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                f2_tu=lambda x: sum(1 for token in x.tokens.values() if token.prolongations))
        # high volume tokens
        stats["high_volume_tokens"] = utils.compute_stats_per_minute (self.transcription_units, split_size,
                                                                    f2_tu=lambda x: sum(1 for token in x.tokens.values()if token.volume is not None and token.volume == df.volume.high))
        # low volume tokens
        stats["low_volume_tokens"] = utils.compute_stats_per_minute (self.transcription_units, split_size,
                                                                    f2_tu=lambda x: sum(1 for token in x.tokens.values() if token.volume is not None and token.volume == df.volume.low))
        # high volume spans
        stats["high_volume_spans"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                    f2_tu=lambda x:len (x.high_volume_spans))
        # low volume spans
        stats["low_volume_spans"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                f2_tu=lambda x:len (x.low_volume_spans))
        # differing volume spans
        stats["differing_volume_spans"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                        f2_tu=lambda x: len(x.high_volume_spans) + len(x.low_volume_spans))
        # slow pace spans
        stats["slow_pace_spans"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                f2_tu=lambda x:len (x.slow_pace_spans))
        # slow pace tokens
        stats["slow_pace_tokens"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                f2_tu=lambda x: sum (1 for token in x.tokens.values() if token.slow_pace))
        # fast pace spans
        stats["fast_pace_spans"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                f2_tu=lambda x:len(x.fast_pace_spans))
        # fast pace tokens
        stats["fast_pace_tokens"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                f2_tu=lambda x: sum(1 for token in x.tokens.values() if token.fast_pace))
        # differing pace spans
        stats["differing_pace_spans"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                    f2_tu=lambda x: len(x.slow_pace_spans) + len(x.fast_pace_spans))
        # overlapping spans
        stats["overlapping_spans"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                    f2_tu=lambda x: len(x.overlapping_spans))
        # overlapping tokens
        stats["overlapping_tokens"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                    f2_tu=lambda x: sum (1 for token in x.tokens.values() if token.overlaps))
        # guessing spans
        stats ["guessing_spans"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                                f2_tu=lambda x: len(x.guessing_spans))

        # creating an empty dictionary to store statistics

        found = False
        # open and read the .csv file to extract annotators' data
        with open(annotators_data_csv, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file, delimiter="\t")
            for row in reader:
                transcript_id = row["NomeFile"]
                # if transcript_id not in stats:
                if transcript_id == self.tr_id:
                    stats["Transcript_ID"] = self.tr_id
                    stats.update(row)
                    found = True

        if not found:
            print(self.tr_id)

        self.statistics = pd.DataFrame(stats.items(), columns=["Statistic", "Value"])


    def __iter__(self):
        for tu in self.transcription_units:
            yield tu
