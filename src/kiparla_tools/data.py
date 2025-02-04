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
import csv # for annotators' statistics

@dataclass
class Turn:
	speaker: str
	transcription_units_ids: List[str] = field(default_factory=lambda: [])
	start: float = 0
	end: float = 0

	def add_tu(self, tu_id):
		self.transcription_units_ids.append(tu_id)

	def set_start(self, start):
		self.start = start

	def set_end(self, end):
		self.end = end

@dataclass
class Token:
	text: str
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
	prolongations: Dict[int, int] = field(default_factory=lambda: {})
	warnings: Dict[str, int] = field(default_factory=lambda: collections.defaultdict(int))
	errors: List[str] = field(default_factory=lambda: collections.defaultdict(int))

	def __post_init__(self):

		self.orig_text = self.text

		chars = ["[","]", "(", ")", "<", ">", "°"]

		for char in chars:
			self.text = self.text.replace(char, "")

		# self.orig_text = self.text

		# # STEP 1: check that token has shape '?([a-z]+:*)+[-']?[.,?]
		# # otherwise signal error
		matching_instance = re.fullmatch(r"'?(\p{L}+:*)*\p{L}+[-'~]?:*[.,?]?", self.text)

		if matching_instance is None:
			if self.text == "{P}":
				self.token_type = df.tokentype.shortpause
			elif self.text[0] == "{":
				self.token_type = df.tokentype.metalinguistic
			else:
				self.token_type = df.tokentype.error

			return

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
			# self.text = self.text[:-1]
		elif self.text.endswith("'") or self.text.startswith("'"):
			self.truncation = True
			# self.text = self.text[:-1]

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
			# print(char_id, span_len)
		# 	print(match)
		# input()

		new_text, substitutions = re.subn(r":+", "", self.text)
		if substitutions > 0:
			self.text = new_text

		# check for high volume
		if any(letter.isupper() for letter in self.text):
			self.volume = df.volume.high

		self.text = self.text.lower()

		if all(c == "x" for c in self.text):
			self.unknown = True

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

#TODO: creare funzioni di test

@dataclass
class TranscriptionUnit:
	tu_id : int
	speaker: str
	start: float
	end: float
	duration: float
	annotation: str
	# TODO: handle dialect presence
	# dialect: bool = False
	orig_annotation: str = ""
	include: bool = True
	dialect: bool = False
	# split: bool = False
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

		if self.annotation is None:
			self.include = False
			return

		# non jefferson
		substitutions, new_transcription = pt.clean_non_jefferson_symbols(self.annotation)
		self.warnings["NON_JEFFERSON"] = substitutions
		self.annotation = new_transcription

		# transform metalinguistic annotations and pauses
		new_transcription = pt.meta_tag(self.annotation)
		self.annotation = new_transcription

		# dialect
		new_transcription, self.dialect = pt.check_dialect_sign(self.annotation)
		self.annotation = new_transcription

		# spaces before and after parentheses
		substitutions, new_transcription = pt.check_spaces(self.annotation)
		self.warnings["UNEVEN_SPACES"] += substitutions
		self.annotation = new_transcription

		# leading and trailing pauses
		substitutions, new_transcription = pt.remove_pauses(self.annotation)
		self.warnings["TRIM_PAUSES"] += substitutions
		self.annotation = new_transcription

		# leading and trailing prosodic links
		substitutions, new_transcription = pt.remove_prosodiclinks(self.annotation)
		self.warnings["TRIM_PROSODICLINKS"] += substitutions
		self.annotation = new_transcription

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
		self.text = new_text

		substitutions, new_text = pt.replace_po(self.annotation)
		self.warnings["ACCENTS"] += substitutions
		self.text = new_text

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
			matches_left = list(re.finditer(r"<[^ ][^ )\]]?[^><]*[^ (\[]?>", self.annotation))
			matches_right = list(re.finditer(r">[^ ][^ )\]]?[^><]*[^ (\[]?<", self.annotation))
			tot_spans = (self.annotation.count("<") + self.annotation.count(">"))/2

			if not len(matches_left) + len(matches_right) == tot_spans:
				print(self.annotation)
				print(matches_left)
				print(matches_right)
				input()

			# TODO @Martina check se ho beccato slow e fast bene!
			self.slow_pace_spans = [match.span() for match in matches_left]
			self.fast_pace_spans = [match.span() for match in matches_right]

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

		# remove unit if it only includes non-alphabetic symbols
		if all(c in ["[", "]", "(", ")", "°", ">", "<", "-", "'", "#"] for c in self.annotation):
			self.include = False

		if len(self.annotation) == 0:
			self.include = False

		# TODO: gestire cancelletto

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

					subtokens = re.split(r"(\p{L}'\p{L})", tok)

					if len(subtokens) == 3:
						subtoken1 = subtokens[0]+subtokens[1][:-1]
						subtoken2 = subtokens[1][-1]+subtokens[2]

						start1 = start_pos
						end1 = end_pos - len(tok) + len(subtoken1)

						start2 = end1+1
						end2 = end_pos

						token_id += 1
						new_token = Token(subtoken1)
						new_token.add_span(start1, end1)
						new_token.add_info("SpaceAfter", "No")
						self.tokens[token_id] = new_token

						token_id += 1
						new_token = Token(subtoken2)
						new_token.add_span(start2, end2)
						self.tokens[token_id] = new_token

						# start_pos = end_pos+1
						# end_pos+=1


						# print(subtoken1, subtoken2)
						# input()

					else:
						token_id += 1
						new_token = Token(tok)
						new_token.add_span(start_pos, end_pos)
						self.tokens[token_id] = new_token
					start_pos = end_pos+1
					end_pos+=1

		# print(self.tokens)
		# input()

	def add_token_features(self):

		ids = []
		token_ids = []

		for tok_id, tok in self.tokens.items():
			# print(tok_id, tok, tok.span)
			# print(tok.text, tok.orig_text)
			# input()

			i=0
			# for char in tok.text:
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

		# print(self.annotation)
		# print(self.orig_annotation)

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
	turns: List[Turn] = field(default_factory=lambda: [])
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

	def purge_speakers(self):
		speakers_to_remove = []
		for speaker in self.speakers:
			if self.speakers[speaker] == 0:
				speakers_to_remove.append(speaker)

		for speaker in speakers_to_remove:
			del self.speakers[speaker]

	def find_overlaps(self, duration_threshold=0):

		G = nx.Graph()

		toshift = []

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


	def check_overlaps(self):

		to_remove = []
		for u, v in self.time_based_overlaps.edges():
			if all(df.tokentype.metalinguistic in tok.token_type for tok_id, tok in self.transcription_units_dict[u].tokens.items()) or \
			all(df.tokentype.metalinguistic in tok.token_type for tok_id, tok in self.transcription_units_dict[v].tokens.items()):
				to_remove.append((u, v))

		for u, v in to_remove:
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


	def create_turns(self):

		# calculate turns
		# SP1 : [(T1)-][--][--] ----- [(T3)]-[----]------
		# SP2 : .........      [(T2)  ]............

		prev_speaker = self.transcription_units[0].speaker
		curr_turn = Turn(prev_speaker)
		curr_turn.add_tu(self.transcription_units[0].tu_id)
		curr_turn.set_start(self.transcription_units[0].start)
		curr_turn.set_end(self.transcription_units[0].end) # per ottenere anche la fine del primo turno, altrimenti in mancanza di questo ci restituisce solo lo start

		for tu in self.transcription_units[1:]:

			if tu.include:
				speaker = tu.speaker

				if speaker == prev_speaker:
					curr_turn.add_tu(tu.tu_id)
				else:
					self.turns.append(curr_turn)
					curr_turn = Turn(tu.speaker)
					curr_turn.add_tu(tu.tu_id)
					curr_turn.set_start(tu.start)
					prev_speaker = speaker

				curr_turn.set_end(tu.end)

		self.turns.append(curr_turn)

	# Statistic calculations
	def get_stats (self, annotators_data_csv="data/data_description.csv"):
		num_speakers = len(self.speakers) # number of speakers
		num_tu = len(self.transcription_units) # number of TUs
		num_total_tokens = sum(len(tu.tokens) for tu in self.transcription_units) # total number of tokens

		# average duration of TUs
		duration = [tu.duration for tu in self.transcription_units]
		average_duration = sum(duration)/num_tu

		# number of turns
		num_turns = len(self.turns)

		# average tokens 
		# average_tokens = 

        # creating an empty dictionary to store statistics
		stats = {}

		# open and read the .csv file to extract annotators' data
		with open(annotators_data_csv, "r") as file:
			reader = csv.DictReader(file, delimiter="\t")
			for row in reader:
				transcript_id = row["Transcript_ID"]
    
				if transcript_id not in stats:
					stats[transcript_id] = {
					"num_speakers": int(row["num_speakers"]),
                	"num_tu": int(row["num_tu"]),
               	 	"num_total_tokens": int(row["num_total_tokens"]),
                	"average_duration": float(row["average_duration"]),
                	"num_turns": int(row["num_turns"]),
                	"annotator": [],
                	"reviewer": [],
            		"transcription_type": [],
                	"expertise": [],
                	"accuracy": [],
                	"minutes_experiences": [], 
	 				"sec30": [], 
					"sec60": [], 
					"sec90": [], 
					"sec120": [], 
					"sec_assignment": [], 
					}

				stats[transcript_id]["annotator"].append(row["Annotatore"])
				stats[transcript_id]["reviewer"].append(row["Revisore"])
				stats[transcript_id]["transcription_type"].append(row["Tipo"])
				stats[transcript_id]["expertise"].append(row["Esperto"])
				stats[transcript_id]["accuracy"].append(row["Accurato"])
				stats[transcript_id]["minutes_experience"].append(row["MinutiEsperienza"])
				stats[transcript_id]["sec30"].append(row["Sec30"])
				stats[transcript_id]["sec60"].append(row["Sec60"])
				stats[transcript_id]["sec90"].append(row["Sec90"])
				stats[transcript_id]["sec120"].append(row["Sec120"])
				stats[transcript_id]["sec_assignment"].append(row["SecAssegnazione"])

		print(stats) 

# preparing data for df	
		data_for_df = []
		for transcript_id, data in stats.items():
			full_df_data = {
        		"Transcript_ID": data["transcript_id"],
        		"num_speakers": data["num_speakers"],
        		"num_tu": data["num_tu"],
        		"num_total_tokens": data["num_total_tokens"],
        		"average_duration": data["average_duration"],
        		"num_turns": data["num_turns"],
        		"annotator": data["annotator"],
        		"reviewer": data["reviewer"],
        		"transcription_type": data["transcription_type"],
       			"expertise": data["expertise"],
        		"accuracy": data["accuracy"],
        		"minutes_experience": data["minutes_experience"],
				"sec30": data["sec30"],
				"sec60": data["sec60"],
				"sec90": data["sec90"],
				"sec120": data["sec120"],
				"sec_assignment": data["sec_assignment"],
    		}
    		
			data_for_df.append(full_df_data)

# creating the df 
		self.statistics = pd.DataFrame(data_for_df)

	# self.statistics = pd.DataFrame(stats.items(), columns=["Statistic", "Value"])

def __iter__(self):
	for tu in self.transcription_units:
		yield tu