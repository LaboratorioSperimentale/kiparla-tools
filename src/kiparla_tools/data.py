import collections
import itertools
# import re
import regex as re
import pandas as pd
import networkx as nx
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple

import kiparla_tools.process_text as pt
import kiparla_tools.dataflags as df
import kiparla_tools.utils as utils
import csv # for annotators' statistics


@dataclass
class Token:
    text: str
    id: str
    span: Tuple[int,int] = (0,0)
    token_type: df.tokentype = df.tokentype.linguistic
    orig_text: str = ""
    unknown: bool = False
    intonation_pattern: df.intonation = None
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
    dialect: bool = False
    prolongations: Dict[int, int] = field(default_factory=lambda: {})
    warnings: Dict[str, int] = field(default_factory=lambda: collections.defaultdict(int))
    errors: List[str] = field(default_factory=lambda: collections.defaultdict(int))

    def __post_init__(self):

        self.orig_text = self.text

        chars = ["[","]", "(", ")", "<", ">", "°"]

        for char in chars:
            self.text = self.text.replace(char, "")

        # # STEP 1: check that token has shape '?([a-z]+:*)+[-']?[.,?]
        # # otherwise signal error
        matching_po = re.fullmatch(r"po':*[.,?]?", self.text)
        matching_instance = re.fullmatch(r"['~-]?(\p{L}+:*)*\p{L}+:*[-'~]?[.,?]?", self.text)

        if matching_instance is None:
            if self.text == "{P}":
                self.token_type = df.tokentype.shortpause
                return
            elif self.text[0] == "{":
                self.token_type = df.tokentype.metalinguistic
                return
            elif matching_po is None:
                self.token_type = df.tokentype.error
                return
            # return


        if matching_po:
            # print(self.text)
            self.text, subs_made = re.subn(r"'(:*)",
                                    r"\1'",
                                    self.text)
            # print(self.text)
            # input()
            # self.text = self.text.replace("'")

        # STEP2: find final prosodic features: intonation, truncation and interruptions
        if self.text.endswith("."):
            self.intonation_pattern = df.intonation.descending
            self.text = self.text[:-1] # this line removes the last character of the string (".")
        elif self.text.endswith(","):
            self.intonation_pattern = df.intonation.weakly_ascending
            self.text = self.text[:-1]
        elif self.text.endswith("?"):
            self.intonation_pattern = df.intonation.ascending
            self.text = self.text[:-1]
        elif self.text.endswith("-") or self.text.endswith("~"):
            self.interruption = True
        elif self.text.startswith("-") or self.text.startswith("~"):
            self.interruption = True
        elif self.text.endswith("'") or self.text.startswith("'"):
            if self.text not in {"po'"}:
                self.truncation = True
            # TODO: not truncation if text in dictionary of known words (po')

        # STEP3: at this point we should be left with the bare word with only prolongations

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

        # print(self.text)
        matches = list(re.finditer(r":+", self.text))
        # print(matches)
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

        if all(c == "x" for c in self.text):
            self.token_type = df.tokentype.unknown
            self.text = "x"

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

        if field_name == "Dialect":
            self.dialect = True

#TODO: creare funzioni di test

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
    dialect: bool = False
    overlapping_spans: List[Tuple[int, int]] = field(default_factory=lambda: [])
    overlapping_times: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {})
    overlapping_matches: Dict[Tuple[int, int], str] = field(default_factory=lambda: [])
    overlap_duration: Dict[str, float] = field(default_factory=lambda: {})

    low_volume_spans: List[Tuple[int, int]] = field(default_factory=lambda: [])
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

        self.annotation = self.annotation.strip()

        if self.annotation is None or len(self.annotation)<1:
            self.include = False
            return

        if self.annotation[0] == "#":
            self.dialect = True
            self.annotation = self.annotation[1:]

        functions_to_apply = [
            ("SYMBOL_NOT_ALLOWED", pt.clean_non_jefferson_symbols),   # remove non jefferson symbols
            ("META_TAGS", pt.meta_tag),                               # transform metalinguistic annotations and shortpauses
            ("UNEVEN_SPACES", pt.check_spaces),                       # remove spaces before and after parentheses
            ("TRIM_PAUSES", pt.remove_pauses),                        # remove leading and trailing shortpauses
            ("TRIM_PROSODICLINKS", pt.remove_prosodiclinks),          # remove leading and trailing prosodiclinks
            ("OVERLAP_PROLONGATION", pt.overlap_prolongations),       # fix \w+:*[:
        ]

        for warning_label, function in functions_to_apply:
            substitutions, new_transcription = function(self.annotation)
            self.warnings[warning_label] = substitutions
            self.annotation = new_transcription

        # # non jefferson
        # substitutions, new_transcription = pt.clean_non_jefferson_symbols(self.annotation)
        # self.warnings["NON_JEFFERSON"] = substitutions
        # self.annotation = new_transcription

        # # transform metalinguistic annotations and pauses
        # substitutions, new_transcription = pt.meta_tag(self.annotation)
        # self.warnings["META_TAGS"] = substitutions
        # self.annotation = new_transcription

        # # spaces before and after parentheses
        # substitutions, new_transcription = pt.check_spaces(self.annotation)
        # self.warnings["UNEVEN_SPACES"] += substitutions
        # self.annotation = new_transcription

        # # leading and trailing pauses
        # substitutions, new_transcription = pt.remove_pauses(self.annotation)
        # self.warnings["TRIM_PAUSES"] += substitutions
        # self.annotation = new_transcription

        # # leading and trailing prosodic links
        # substitutions, new_transcription = pt.remove_prosodiclinks(self.annotation)
        # self.warnings["TRIM_PROSODICLINKS"] += substitutions
        # self.annotation = new_transcription

        # # fix \w+:*[:
        # substitutions, new_transcription = pt.overlap_prolongations(self.annotation)
        # self.warnings["OVERLAP_PROLONGATION"] += substitutions
        # self.annotation = new_transcription

        # remove double spaces
        substitutions, new_transcription = pt.remove_spaces(self.annotation)
        self.warnings["UNEVEN_SPACES"] += substitutions
        self.annotation = new_transcription

        self.errors["UNBALANCED_DOTS"] = not pt.check_even_dots(self.annotation)
        self.errors["UNBALANCED_OVERLAP"] = not pt.check_normal_parentheses(self.annotation, "[", "]")
        self.errors["UNBALANCED_GUESS"] = not pt.check_normal_parentheses(self.annotation, "(", ")")
        self.errors["UNBALANCED_PACE"] = not pt.check_angular_parentheses(self.annotation)

        #pò, perché etc..
        substitutions, new_text = pt.replace_che(self.annotation)
        self.warnings["ACCENTS"] += substitutions
        self.annotation = new_text

        substitutions, new_text = pt.replace_po(self.annotation)
        self.warnings["ACCENTS"] += substitutions
        self.annotation = new_text

        substitutions, new_text = pt.replace_pero(self.annotation)
        self.warnings["ACCENTS"] += substitutions
        self.annotation = new_text

        # substitute numbers
        substitutions, new_transcription = pt.check_numbers(self.annotation)
        self.warnings["NUMBERS"] = substitutions
        self.annotation = new_transcription

        # fix spaces before and after dots
        if "°" in self.annotation and not self.errors["UNBALANCED_DOTS"]:
            substitutions, new_transcription = pt.check_spaces_dots(self.annotation)
            self.warnings["UNEVEN_SPACES"] += substitutions
            self.annotation = new_transcription

        # fix spaces before and after angular
        if "<" in self.annotation and not self.errors["UNBALANCED_PACE"]:
            substitutions, new_transcription = pt.check_spaces_angular(self.annotation)
            self.warnings["UNEVEN_SPACES"] += substitutions
            self.annotation = new_transcription

        # check how many varying pace spans have been transcribed
        if "<" in self.annotation and not self.errors["UNBALANCED_PACE"]:

            tot_spans = (self.annotation.count("<") + self.annotation.count(">"))/2
            # OLD VERSION
            # matches_left = list(re.finditer(r"<[^ ][^ )\]]?[^><]*[^ (\[]?>", self.annotation))
            # matches_right = list(re.finditer(r">[^ ][^ )\]]?[^><]*[^ (\[]?<", self.annotation))
            matches_left, matches_right = pt.matches_angular(self.annotation)

            # TODO @Martina check se ho beccato slow e fast bene!
            # self.slow_pace_spans = [match.span() for match in matches_left]
            # self.fast_pace_spans = [match.span() for match in matches_right]
            self.slow_pace_spans = [x[1] for x in matches_left]
            self.fast_pace_spans = [x[1] for x in matches_right]

        # check how many low volume spans have been transcribed
        if "°" in self.annotation and not self.errors["UNBALANCED_DOTS"]:
            matches = list(re.finditer(r"°[^°]+°", self.annotation))
            if len(matches)>0:
                self.low_volume_spans = [match.span() for match in matches]

        # check how many overlapping spans have been transcribed
        if "[" in self.annotation and not self.errors["UNBALANCED_OVERLAP"]:
            matches = list(re.finditer(r"\[[^\]]+\]", self.annotation))
            if len(matches)>0:
                self.overlapping_spans = [match.span() for match in matches]

        # check how many guessing spans have been transcribed
        if "(" in self.annotation and not self.errors["UNBALANCED_GUESS"]:
            matches = list(re.finditer(r"\([^)]+\)", self.annotation))
            if len(matches)>0:
                self.guessing_spans = [match.span() for match in matches]

        # invert [.,?][:-~]
        substitutions, new_transcription = pt.switch_symbols(self.annotation)
        self.warnings["SWITCHES"] += substitutions
        self.annotation = new_transcription

        # remove unit if it only includes non-alphabetic symbols
        if all(c in ["[", "]", "(", ")", "°", ">", "<", "-", "'", "#"] for c in self.annotation):
            self.include = False

        if len(self.annotation) == 0:
            self.include = False


    def tokenize(self):

        if not self.include:
            return

        # print(self.annotation)
        # ! split on space, apostrophe between words and prosodic links
        # tokens = re.split(r"( |(?<=\w)'(?=\w)|=)", self.annotation)
        tokens = re.split(r"( |=)", self.annotation)

        start_pos = 0
        end_pos = 0
        token_id = -1

        for tok in tokens:

            if len(tok)>0 and not tok == " ":
                end_pos += len(tok)
                if tok == "=":
                    if len(self.tokens) == 0:
                        self.warnings["SKIPPED_TOKEN"] += 1
                    else:
                        self.tokens[token_id].add_info("ProsodicLink", "Yes")
                    start_pos = end_pos+1
                else:

                    subtokens = re.split(r"(\p{L}[\)\]°><]?'[\(\[°><]?\p{L})", tok)

                    if len(subtokens) == 3:
                        subtoken1 = subtokens[0]+subtokens[1][:-1]
                        subtoken2 = subtokens[1][-1]+subtokens[2]

                        start1 = start_pos
                        end1 = end_pos - len(tok) + len(subtoken1) -1

                        start2 = end1+1
                        end2 = end_pos

                        token_id += 1
                        new_token = Token(subtoken1, f"{self.tu_id}-{token_id}")
                        new_token.add_span(start1, end1)
                        new_token.add_info("SpaceAfter", "No")
                        self.tokens[token_id] = new_token

                        token_id += 1
                        new_token = Token(subtoken2, f"{self.tu_id}-{token_id}")
                        new_token.add_span(start2, end2)
                        self.tokens[token_id] = new_token

                    else:
                        token_id += 1
                        new_token = Token(tok, f"{self.tu_id}-{token_id}")
                        new_token.add_span(start_pos, end_pos)
                        self.tokens[token_id] = new_token
                    start_pos = end_pos+1
                    end_pos+=1


        if self.dialect:
            for tok_id, tok in self.tokens.items():
                tok.add_info("OrigLang", "dialect")

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
                                    ("guesses", self.guessing_spans)]:



            for span_id, span in enumerate(spans):
                a, b = span[0], span[1]

                data = list(zip(token_ids[a:b], ids[a:b]))
                unique_tokens = set(x for x,y in data if x > -1)

                char_ranges = {x:[] for x in unique_tokens}
                for token_id, pos_id in data:
                    if token_id in char_ranges:
                        char_ranges[token_id].append(pos_id)

                for id in char_ranges:
                    char_ranges[id] = (min(char_ranges[id]), max(char_ranges[id])+1)
                    self.tokens[id].add_info(feature_name, (span_id,
                                                            char_ranges[id][0],
                                                            char_ranges[id][1]))


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
            self.tokens[0].position_in_tu = df.position.start
            self.tokens[max(self.tokens.keys())].position_in_tu = df.position.end


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

                        if duration < duration_threshold:
                            duration1 = tu1.end-tu1.start
                            duration2 = tu2.end-tu2.start

                            if duration1 > duration2:
                                tu1.end = tu1.end - duration_threshold
                                tu1.warnings["MOVED_BOUNDARIES"] += 1

                            else:
                                tu2.start = tu2.start + duration_threshold
                                tu2.warnings["MOVED_BOUNDARIES"] += 1

                        else:

                            G.add_edge(tu1.tu_id, tu2.tu_id,
                                        start = start,
                                        end = end,
                                        duration = duration,
                                        spans = {tu1.tu_id:None, tu2.tu_id:None})

        self.time_based_overlaps = G


    def check_overlaps(self, relations_to_ignore = []):

        to_remove = []
        for u, v in self.time_based_overlaps.edges():
            if all(df.tokentype.metalinguistic in tok.token_type for tok_id, tok in self.transcription_units_dict[u].tokens.items()) or \
            all(df.tokentype.metalinguistic in tok.token_type for tok_id, tok in self.transcription_units_dict[v].tokens.items()):
                to_remove.append((u, v))

        for u, v in to_remove:
            self.time_based_overlaps.remove_edge(u, v)

        if len(relations_to_ignore):
            for u, v in relations_to_ignore:
                self.time_based_overlaps.remove_edge(u, v)

        cliques = sorted(nx.find_cliques(self.time_based_overlaps), key=lambda x: len(x))

        for clique in cliques:

            if len(clique)>1:
                starts = []
                ends = []

                for node in clique:
                    starts.append(self.transcription_units_dict[node].start)
                    ends.append(self.transcription_units_dict[node].end)

                overlap_start = max(starts)
                overlap_end = min(ends)

                for node in clique:
                    clique_tup = tuple(x for x in clique if not x == node)
                    self.transcription_units_dict[node].overlapping_times[clique_tup] = (overlap_start, overlap_end)

        edges_to_move = []

        for tu_id, tu  in self.transcription_units_dict.items():
            spans = tu.overlapping_spans
            times = tu.overlapping_times

            if len(spans) == len(times):
                sorted_overlaps = list(sorted(tu.overlapping_times.items(), key=lambda x: x[1][0]))
                sorted_overlaps = ["+".join([str(el) for el in x]) for x, y in sorted_overlaps]
                tu.overlapping_matches = dict(zip(tu.overlapping_spans, sorted_overlaps))

            elif len(spans) == 0:
                tu.errors["MISMATCHING_OVERLAPS"] = True

                for el in tu.overlapping_times:
                    tu.overlap_duration["+".join([str(x) for x in el])] = tu.overlapping_times[el][1]-tu.overlapping_times[el][0]
            elif len(times) == 0:
                tu.errors["MISMATCHING_OVERLAPS"] = True
                sorted_overlaps = ["?" for el in tu.overlapping_spans]
                tu.overlapping_matches = dict(zip(tu.overlapping_spans, sorted_overlaps))

            else:
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

        # number of tokens per minute
        stats["tokens_per_minute"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                            f2_tu=lambda x: len(x.tokens))

        # totale dei minuti trascritti
        stats["transcribed_minutes"] = utils.compute_stats_per_minute(self.transcription_units, split_size,
                                                            f2_tu=lambda x: x.duration)
        # average number of token/minute
        # avg_tokens_per_min = sum(tokens_per_minute) / len(tokens_per_minute)
        stats["avg_tokens_per_min"] = []
        for n_tokens, n_tus in zip(stats["tokens_per_minute"], stats["num_tu"]):
            if n_tus > 0:
                stats["avg_tokens_per_min"].append(n_tokens / n_tus)
            else:
                stats["avg_tokens_per_min"].append(0)


        # stats["avg_duration_per_min"] = []
        # for n_tokens, n_tus in zip(stats["duration_per_minute"], stats["num_tu"]):
        #     if n_tus > 0:
        #         stats["avg_duration_per_min"].append(n_tokens / n_tus)
        #     else:
        #         stats["avg_duration_per_min"].append(0)

        # # number of total overlaps
        # num_overlaps = []
        # curr_overlaps = 0

        # for tu in self.transcription_units:
        #     if tu.end < split_size*i:
        #         curr_overlaps += len(tu.overlapping_times)
        #     else:
        #         num_overlaps.append(curr_overlaps)
        #         duration_curr += tu.duration
        #         i += 1
        #     num_overlaps += (len(tu.overlapping_times))

        # # number of intonation patterns
        # num_intonation_patterns = 0
        # for tu in self.transcription_units:
        #     for token in tu.tokens.values():
        #         if token.intonation_pattern is not None:
        #             num_intonation_patterns += 1

        # # number of low volume spans
        # num_low_volume_spans = 0

        # for tu in self.transcription_units:
        #     num_low_volume_spans += (len(tu.low_volume_spans))

        # # number of guessing spans
        # num_guessing_spans = 0

        # for tu in self.transcription_units:
        #     num_guessing_spans += (len(tu.guessing_spans))

        # # number of fast pace spans
        # num_fast_pace_spans = 0

        # for tu in self.transcription_units:
        #     num_fast_pace_spans += (len(tu.fast_pace_spans))

        # # number of slow pace spans
        # num_slow_pace_spans = 0

        # for tu in self.transcription_units:
        #     num_slow_pace_spans += (len(tu.slow_pace_spans))

        # # number of prolongations
        # # prolongations: Dict[int, int] = field(default_factory=lambda: {}) --> attributo della classe token
        # num_prolongations = 0

        # for tu in self.transcription_units:
        #     for token in tu.tokens.values():
        #         num_prolongations += (len(token.prolongations))

        # #num_linguistic token type
        # num_linguistic_tokens = 0
        # for tu in self.transcription_units:
        #     for token in tu.tokens.values():
        #         if token.token_type & df.tokentype.linguistic:
        #             num_linguistic_tokens +=1

        # # number of linguistic token per minute
        # ling_tokens_per_min = []
        # i = 1
        # ling_tokens_curr = 0
        # for tu in self.transcription_units:
        #     if tu.end < split_size*i:
        #         for token in tu.tokens.values():
        #             if token.token_type & df.tokentype.linguistic:
        #                 ling_tokens_curr += 1
        #     else:
        #         ling_tokens_per_min.append(ling_tokens_curr)
        #         for token in tu.tokens.values():
        #             if token.token_type & df.tokentype.linguistic:
        #                 ling_tokens_curr += 1
        #         i += 1
        # ling_tokens_per_min.append(ling_tokens_curr)

        # # num_metalinguistic token type
        # num_metaling_tokens = 0
        # for tu in self.transcription_units:
        #     for token in tu.tokens.values():
        #         if token.token_type & df.tokentype.metalinguistic:
        #             num_metaling_tokens += 1

        # # num_shortpauses
        # num_shortpauses = 0
        # for tu in self.transcription_units:
        #     for token in tu.tokens.values():
        #         if token.token_type & df.tokentype.shortpause:
        #             num_shortpauses += 1

        # #num_unknown
        # num_unknown = 0
        # for tu in self.transcription_units:
        #     for token in tu.tokens.values():
        #         if token.token_type & df.tokentype.unknown:
        #             num_unknown += 1

        # #num_errors
        # num_errors = 0
        # for tu in self.transcription_units:
        #     for token in tu.tokens.values():
        #         if token.token_type & df.tokentype.error:
        #             num_errors += 1

        # creating an empty dictionary to store statistics


        # open and read the .csv file to extract annotators' data
        with open(annotators_data_csv, "r") as file:
            reader = csv.DictReader(file, delimiter="\t")
            for row in reader:
                transcript_id = row["NomeFile"]

                # if transcript_id not in stats:
                if transcript_id == self.tr_id:
                    stats["Transcript_ID"] = self.tr_id
                    stats.update(row)
                    # stats["annotator"]= row["Annotatore"]
                    # stats["reviewer"]= row["Revisore"]
                    # stats["transcription_type"]= row["Tipo"]
                    # stats["expertise"]= row["Esperto"]
                    # stats["accuracy"]= row["Accurato"]
                    # stats["minutes_experience"]= row["MinutiEsperienza"]
                    # stats["sec30"]= row["Sec30"]
                    # stats["sec60"]= row["Sec60"]
                    # stats["sec90"]: row["Sec90"]
                    # stats["sec120"]: row["Sec120"]
                    # stats["sec_assignment"]: row["SecAssegnazione"]


        self.statistics = pd.DataFrame(stats.items(), columns=["Statistic", "Value"])


    def __iter__(self):
        for tu in self.transcription_units:
            yield tu
