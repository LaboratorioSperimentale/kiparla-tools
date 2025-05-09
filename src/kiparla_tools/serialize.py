import csv
from ast import literal_eval
import regex as re
import pandas as pd
import yaml
from speach import elan
from pympi import Elan as EL
import logging
import collections

from kiparla_tools import data
from kiparla_tools import dataflags as df
from kiparla_tools.logging_utils import setup_logging

from kiparla_tools.config_parameters import (
	CONLL_FIELDNAMES
)

logger = logging.getLogger(__name__)
setup_logging(logger)



def conll2conllu(filename, output_filename):

	# ID FORM LEMMA UPOS XPOS FEATS HEAD DEPREL DEPS MISC
	with open(filename, encoding="utf-8") as fin, open(output_filename, "w", encoding="utf-8") as fout:
		for unit_id, unit in units_from_conll(fin):
			metadata = {
				"sent_id" : unit_id,
				"text": "",
				"jefferson_text": "",
				"tu_ids": set(u["tu_id"] for u in unit)
			}

			tokens = []

			for token in unit:
				conllu_tok = {
					"ID": token["id"],
					"FORM": token["form"],
					"LEMMA": token["lemma"],
					"UPOS": token["upos"],
					"XPOS": token["xpos"],
					"FEATS": token["feats"],
					"HEAD": "_",
					"DEPREL": "_",
					"DEPS": "_",
					"MISC": "_",
				}

				if not token["deprel"] == "_":
					deprel, head = token["deprel"].rsplit(":", 1)
					head = int(head)
					conllu_tok["HEAD"] = head
					conllu_tok["DEPREL"] = deprel

				if not token["token_id"] == "_":
					if "SpaceAfter" in token["jefferson_feats"]:
						metadata["text"] += token["form"]
						metadata["jefferson_text"] += token["span"]

					elif "ProsodicLink" in token["jefferson_feats"]:
						metadata["text"] += " "+token["form"]
						metadata["jefferson_text"] += "="+token["span"]

					else:
						metadata["text"] += token["form"]+" "
						metadata["jefferson_text"] += token["span"]+" "

				feats = {}
				if not token["token_id"] == "_":
					feats["TID"] = token["token_id"]
				if not token["speaker"] == "_":
					feats["Speaker"] = token["speaker"]

				if not token["jefferson_feats"] == "_":
					jefferson_features = token["jefferson_feats"].split("|")

					for element in jefferson_features:
						element = element.strip()
						if len(element):
							element = element.split("=")
							feats[element[0]] = element[1]

				if token["type"] in ["error", "shortpause", "unknown"]:
					feats["Type"] = token["type"]
				elif token["type"] == "metalinguistic":
					feats["Type"] = token["meta_label"]

				if len(token["align"]) and not token["align"] == "_":
					align, ms = token["align"].split("=")
					feats[f"Align{align.capitalize()}"] = ms

				if len(token["prolongations"]) and not token["prolongations"] == "_":
					feats["Prolonged"] = "Yes"

				if len(token["pace"]) and not token["pace"] == "_":
					paces, _ = token["pace"].split("=")
					feats[f"Pace{paces.capitalize()}"] = "Yes"

				if not token["overlaps"] == "_":
					feats["Overlapping"] = "Yes"


				conllu_tok["MISC"] = "|".join(list(f"{x}={y}" for x, y in sorted(feats.items())))
				if not conllu_tok["MISC"].strip():
					conllu_tok["MISC"] = "_"
				tokens.append(conllu_tok)


			print(f"# sent_id = {metadata['sent_id']}", file=fout)
			print(f"# text = {metadata['text'].strip()}", file=fout)
			print(f"# jefferson_text = {metadata['jefferson_text']}", file=fout)
			for tok in tokens:
				print(f"{tok['ID']}\t{tok['FORM']}\t{tok['LEMMA']}\t{tok['UPOS']}\t{tok['XPOS']}\t{tok['FEATS']}\t{tok['HEAD']}\t{tok['DEPREL']}\t{tok['DEPS']}\t{tok['MISC']}", file=fout)
			print("", file=fout)

def units_from_conll(fobj, source_col="unit"):
	curr_sent = []
	curr_unit = "0"
	reader = csv.DictReader(fobj, delimiter="\t")
	for row in reader:
		token_id = row["token_id"]
		type = row["type"]
		text = row["form"]
		unit = row[source_col]

		if unit == curr_unit or unit == "_":
			curr_sent.append(row)
		else:
			if len(curr_sent):
				yield curr_unit, curr_sent
			curr_unit = unit
			curr_sent = [row]

	if len(curr_sent):
		yield curr_unit, curr_sent


def print_full_statistics(list_of_transcripts, output_filename):
	"""
	The function processes a list of transcripts to calculate statistics and outputs them to a
	specified file in tab-separated format.

	:param list_of_transcripts: `list_of_transcripts` is a dictionary where the keys are transcript IDs
	and the values are objects representing transcripts. Each transcript object has a method
	`get_stats()` that calculates statistics for that transcript and stores them in a DataFrame
	attribute called `statistics`
	:param output_filename: The `output_filename` parameter in the `print_full_statistics` function is a
	string that represents the name of the file where the statistics for each transcript will be saved.
	This file will be in CSV format and will contain the calculated statistics for each transcript in a
	structured manner.
	"""

	max_columns = 0
	full_statistics = [] # list that contains all transcripts
	for _, transcript in list_of_transcripts.items(): # iterating each transcript
		transcript.get_stats() # calculating statistics
		stats_dict = transcript.statistics.set_index("Statistic")["Value"].to_dict() # converting statistics into a dictionary
		if len(stats_dict["num_tu"]) > max_columns:
			max_columns = len(stats_dict["num_tu"])
		full_statistics.append(stats_dict)

	for stats in full_statistics:
		fields = list(stats.keys())
		for field in fields:
			if type(stats[field]) is list:
				for el in range(max_columns):
					stats[f"{field}::{el}"] = stats[field][el] if len(stats[field])>el else 0
				del stats[field]

	# Creating a df with all statistics
	statistics_complete = pd.DataFrame(full_statistics) # creating the dataframe
	statistics_complete.to_csv(output_filename, index=False, sep="\t") # converting the df to csv


def conversation_to_conll(transcript, output_filename, sep = '\t'):
	"""
	The function `conversation_to_conll` converts a conversation transcript into a CoNLL format and
	writes it to an output file.

	:param transcript: transcript object to be serialized.
	:param output_filename: name of the file where the output CONLL data will be written.
	This file will be created or overwritten if it already exists.
	:param sep: delimiter that separates the fields in the output file.
	"""

	with open(output_filename, "w", encoding="utf-8", newline='') as fout:
		writer = csv.DictWriter(fout, fieldnames=CONLL_FIELDNAMES, delimiter=sep, restval="_")
		writer.writeheader()

		for tu in transcript.transcription_units:
			tu_id = tu.tu_id

			for _, tok in tu.tokens.items():

				to_write = {"token_id": tok.id,
							"speaker": tu.speaker,
							"tu_id": tu_id,
							"form": tok.text,
							"type": tok.token_type.name,
							}

				jefferson_feats = {"intonation": f"Intonation={tok.intonation_pattern.name}" if tok.intonation_pattern else "_",
									"interruption": "Interrupted=Yes" if tok.interruption else "_",
									"truncation": "Truncated=Yes" if tok.truncation else "_",
									"prosodicLink": "ProsodicLink=Yes" if tok.prosodiclink else "_",
									"spaceafter": "SpaceAfter=No" if not tok.spaceafter else "_",
									"dialect": "Dialect=Yes" if tok.dialect else "_",
									"volume": f"Volume={tok.volume.name}" if tok.volume else "_"}

				to_write["jefferson_feats"] = "|".join([x for x in jefferson_feats.values() if not x == "_"]) #TODO: rewrite

				to_write["span"] = tu.annotation[tok.span[0]:tok.span[1]]

				align = []
				if df.position.start in tok.position_in_tu:
					align.append(("Begin", tu.start))
				if df.position.end in tok.position_in_tu:
					align.append(("End", tu.end))
				if len(align):
					to_write["align"] = "|".join([f"{x[0]}={x[1]}" for x in align])

				to_write["prolongations"] = ",".join([f"{x[0]}x{x[1]}" for x in tok.prolongations.items()])

				slow_pace = []
				for span_id, span in tok.slow_pace.items():
					slow_pace.append(f"{span[0]}-{span[1]}({span_id})")

				fast_pace = []
				for span_id, span in tok.fast_pace.items():
					fast_pace.append(f"{span[0]}-{span[1]}({span_id})")

				if len(slow_pace) or len(fast_pace):
					to_write["pace"] = ""
					if len(slow_pace):
						to_write["pace"] = "Slow="+",".join(slow_pace)
					if len(fast_pace):
						if len(to_write["pace"]):
							to_write["pace"] += "|"
						to_write["pace"] += "Fast="+",".join(fast_pace)

					# to_write["pace"] = ",".join(slow_pace) if len(slow_pace) > 0 else "_"

				guesses = []
				for span_id, span in tok.guesses.items():
					guesses.append(f"{span[0]}-{span[1]}({span_id})")
				if len(guesses):
					to_write["guesses"] = ",".join(guesses) if len(guesses) > 0 else "_"

				overlaps = []
				for span_id, span in tok.overlaps.items():
					overlaps.append(f"{span[0]}-{span[1]}({span_id})")
				if len(overlaps):
					to_write["overlaps"] = ",".join(overlaps) if len(overlaps) > 0 else "_"

				writer.writerow(to_write)


def conversation_to_linear(transcript, output_filename, sep = '\t'):

	fieldnames = ["tu_id", "speaker", "start", "end", "duration", "include", "variation",
				"W:normalized_spaces", "W:numbers", "W:accents", "W:non_jefferson", "W:pauses_trim", "W:prosodic_trim", "W:moved_boundaries", "W:switches",
				"E:volume", "E:pace", "E:guess", "E:overlap", "E:overlap_mismatch",
				"E:overlap_duration", "E:unmatched_overlaps",
				"T:shortpauses", "T:metalinguistic", "T:errors", "T:linguistic",
				"original", "text", "orthographic"]

	with open(output_filename, "w", encoding="utf-8") as fout:
		writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=sep, restval="_")
		writer.writeheader()

		for tu in transcript.transcription_units:

			to_write = {
						"tu_id": tu.tu_id,
						"speaker": tu.speaker,
						"start": tu.start,
						"end": tu.end,
						"duration": tu.duration,
						"include": tu.include,
						"variation": tu.dialect,
						"original": tu.orig_annotation,
						"text": tu.annotation,
						"orthographic": " ".join(str(tok) for _, tok in tu.tokens.items()),
						"W:normalized_spaces": tu.warnings["UNEVEN_SPACES"],
						"W:numbers": tu.warnings["NUMBERS"],
						"W:accents": tu.warnings["ACCENTS"],
						"W:non_jefferson": tu.warnings["NON_JEFFERSON"],
						"W:pauses_trim": tu.warnings["TRIM_PAUSES"],
						"W:prosodic_trim": tu.warnings["TRIM_PROSODICLINKS"],
						"W:moved_boundaries": tu.warnings["MOVED_BOUNDARIES"],
						"W:switches": tu.warnings["SWITCHES"],
						"E:volume": tu.errors["UNBALANCED_DOTS"],
						"E:pace": tu.errors["UNBALANCED_PACE"],
						"E:guess": tu.errors["UNBALANCED_GUESS"],
						"E:overlap": tu.errors["UNBALANCED_OVERLAP"],
						"E:overlap_mismatch": tu.errors["MISMATCHING_OVERLAPS"],
						"E:unmatched_overlaps": tu.errors["UNMATCHED_OVERLAPS"],
						"T:shortpauses": sum([df.tokentype.shortpause in tok.token_type for _, tok in tu.tokens.items()]),
						"T:metalinguistic": sum([df.tokentype.metalinguistic in tok.token_type for _, tok in tu.tokens.items()]),
						"T:errors": sum([df.tokentype.error in tok.token_type for _, tok in tu.tokens.items()]),
						"T:linguistic": sum([df.tokentype.linguistic in tok.token_type for _, tok in tu.tokens.items()])
					}

			errors = " ".join([tok.text for _, tok in tu.tokens.items() if df.tokentype.error in tok.token_type])
			to_write["T:errors"] = f"{to_write['T:errors']}"
			if len(errors):
				to_write["T:errors"]+=f", {errors}"
			if len(tu.overlap_duration) > 0:
				overlaps = []
				for unit_id, duration in tu.overlap_duration.items():
					overlaps.append(f"{unit_id}={duration:.3f}")

				to_write["E:overlap_duration"] = ",".join(overlaps)

			writer.writerow(to_write)


def csv2eaf(input_filename, linked_file, output_filename,
			sep="\t", multiplier=1000, include_ids = False):
	"""
	Reads data from a tab-separated CSV (.eaf) file and writes it to a ELAN file.

	:param input_filename: name of the input file that contains the data in `csv` format
	:param output_filename: name of the file where the output EAF data will be written.
	This file will be created or overwritten if it already exists.
	:param sep: delimiter that will be used to parse the input CSV file.
	"""

	tus = []
	tiers = set()
	with open(input_filename, encoding="utf-8") as csvfile:
		reader = csv.DictReader(csvfile, delimiter=sep)
		for row in reader:
			if "speaker" in row:
				tiers.add(row["speaker"])
				tus.append(row)

	doc = EL.Eaf(author="automatic_pipeline")

	doc.add_linked_file(linked_file, relpath=linked_file)

	for tier_id in tiers:
		doc.add_tier(tier_id=tier_id)

	for annotation in tus:
		if not "include" in annotation or literal_eval(annotation["include"]):

			value = annotation['text']
			if include_ids:
				value=f"id:{annotation['tu_id']} {annotation['text']}"
			# print(annotation["start"], annotation["end"], annotation["text"])
			start = int(float(annotation["start"])*multiplier)
			end = int(float(annotation["end"])*multiplier)
			logger.debug(f"Adding annotation: {annotation['speaker']} {start} {end} {value}")
			if end - start < 0:
				logger.error(f"Negative duration for {annotation['speaker']} {start} {end} {value}")

			doc.add_annotation(id_tier = annotation["speaker"],
								start=int(float(annotation["start"])*multiplier),
								end=int(float(annotation["end"])*multiplier),
								value=value
							)
	doc.to_file(output_filename)


def eaf2csv(input_filename, output_filename, annotations, sep="\t"):
	"""
	Reads data from an ELAN (.eaf) file and writes it to a CSV file with specified fieldnames and separator.

	:param input_filename: name of the input file that contains the data in `eaf` format
	:param output_filename: name of the file where the output CSV data will be written.
	This file will be created or overwritten if it already exists.
	:param sep: delimiter that will be used in the output CSV file.
	"""

	fieldnames = ["tu_id", "speaker", "start", "end", "duration", "text"]

	full_file = []

	eaf = elan.read_eaf(input_filename)
	for tier in eaf:
		for anno in tier.annotations:
			_from_ts = f"{anno.from_ts.sec:.3f}" if anno.from_ts is not None else ''
			_to_ts = f"{anno.to_ts.sec:.3f}" if anno.to_ts is not None else ''
			_duration = f"{anno.duration:.3f}" if anno.duration is not None else ''

			to_write = {"speaker": tier.ID,
						"start": _from_ts,
						"end": _to_ts,
						"duration": _duration,
						"id": None
						# "text": re.sub(r"^id:[0-9]+", "", anno.value.strip()) # TODO: substitute {} with (())
						}
			text_matches = re.split(r"^(id:)([0-9]+) ", anno.value.strip())

			to_write["text"] = text_matches[-1]
			if len(text_matches)>1:
				to_write["id"] = text_matches[2] # due to crazy python: re.split(r"^(id:)([0-9]+) ", "id:15 ciao ciao") ->  ['', 'id:', '15', 'ciao ciao']
			full_file.append(to_write)

	to_remap = {}

	full_file = sorted(full_file, key=lambda x: float(x["start"]))

	with open(output_filename, "w", encoding="utf-8", newline='') as fout:
		writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=sep, extrasaction='ignore')
		writer.writeheader()
		for el_no, to_write in enumerate(full_file):
			to_write["tu_id"] = el_no
			to_remap[to_write["id"]] = el_no

			writer.writerow(to_write)

	if "ignore" in annotations:
		for pos, el_list in enumerate(annotations["ignore"]):
			el_list = el_list.split()
			new_list = []
			for x in el_list:
				x = int(x)
				if x in to_remap:
					new_list.append(str(to_remap[x]))
				else:
					new_list.append(str(x))
			annotations["ignore"][pos] = " ".join(new_list)


def read_csv(input_filename, sep="\t"):
	"""
	Reads a CSV file representing a transcript and yields specific columns as tuples.

	:param input_filename: name of the CSV containing the transcript.
	The columns being extracted are "tu_id", "speaker", "start", "end", "duration", "text"
	:param sep: delimiter that separates the fields in the CSV file.
	"""

	with open(input_filename, encoding="utf-8", newline='') as csvfile:
		reader = csv.DictReader(csvfile, delimiter=sep)

		for row in reader:
			yield int(row["tu_id"]), row["speaker"], \
					float(row["start"]), float(row["end"]), float(row["duration"]), \
					row["text"]


def tokens_from_conll(input_filename, sep="\t"):
	with open(input_filename, encoding="utf-8", newline='') as csvfile:
		reader = csv.DictReader(csvfile, delimiter=sep)

		for row in reader:
			yield data.Token(row["token"], row["token_id"])


def transcript_from_csv(input_filename, sep="\t"):

	transcript = data.Transcript(input_filename.stem)
	with open(input_filename, encoding="utf-8", newline='') as csvfile:
		reader = csv.DictReader(csvfile, delimiter=sep)

		for row in reader:
			new_tu = data.TranscriptionUnit(row["tu_id"],
											row["speaker"],
											float(row["start"]),
											float(row["end"]),
											float(row["duration"]),
											row["correct"])
			transcript.add(new_tu)

	transcript.sort()

	for tu in transcript:
		tu.tokenize()

	return transcript

def print_aligned(tokens_a, tokens_b, output_filename, sep="\t"):

	fieldnames = ["match", "id_A", "token_A", "id_B", "token_B"]

	with open(output_filename, "w", encoding="utf-8") as fout:
		writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=sep, restval="_")
		writer.writeheader()

		for toka, tokb in zip(tokens_a, tokens_b):
			to_write = {"match": 2,
						"id_A": "_",
						"token_A": "_",
						"id_B": "_",
						"token_B": "_"}
			if toka:
				to_write["token_A"] = toka.text
				to_write["id_A"] = toka.id
				to_write["match"] = 1

			if tokb:
				to_write["token_B"] = tokb.text
				to_write["id_B"] = tokb.id
				if to_write["match"] == 1:
					to_write["match"] = 2
				else:
					to_write["match"] = 1

			if to_write["token_A"] == to_write["token_B"]:
				to_write["match"] = 0

			writer.writerow(to_write)


def load_annotations(fname):

	with open(fname, 'r') as file:
		ret = yaml.safe_load(file)

	return ret

def build_json(transcript):
	ret = {}

	ret["transcript"] = transcript.tr_id
	ret["speakers"] = {x: collections.defaultdict(int) for x in transcript.speakers}
	ret["spoken time"] = 0
	ret["tot tokens"] = 0
	ret["tot tokens-ling"] = 0
	ret["tot tokens-unk"] = 0
	ret["tot tokens-anonym"] = 0
	ret["tot tokens-meta"] = 0
	ret["tot tokens-pause"] = 0
	ret["tot tokens-err"] = 0

	for unit in transcript:
		ret["speakers"][unit.speaker]["TUs"] += 1
		ret["speakers"][unit.speaker]["time"] += unit.duration
		ret["speakers"][unit.speaker]["tokens-ling"] += len([x for x in unit.tokens.values() if df.tokentype.linguistic in x.token_type])
		ret["speakers"][unit.speaker]["tokens-unk"] += len([x for x in unit.tokens.values() if df.tokentype.unknown in x.token_type])
		ret["speakers"][unit.speaker]["tokens-anonym"] += len([x for x in unit.tokens.values() if df.tokentype.anonymized in x.token_type])
		ret["speakers"][unit.speaker]["tokens-meta"] += len([[x for x in unit.tokens.values() if df.tokentype.metalinguistic in x.token_type]])
		ret["speakers"][unit.speaker]["tokens-pause"] += len([x for x in unit.tokens.values() if df.tokentype.shortpause in x.token_type])
		ret["speakers"][unit.speaker]["tokens-err"] += len([x for x in unit.tokens.values() if df.tokentype.error in x.token_type])

		ret["spoken time"] += unit.duration
		ret["tot tokens"] += len(unit.tokens)
		ret["tot tokens-ling"] += len([x for x in unit.tokens.values() if df.tokentype.linguistic in x.token_type])
		ret["tot tokens-unk"] += len([x for x in unit.tokens.values() if df.tokentype.unknown in x.token_type])
		ret["tot tokens-anonym"] += len([x for x in unit.tokens.values() if df.tokentype.anonymized in x.token_type])
		ret["tot tokens-meta"] += len([[x for x in unit.tokens.values() if df.tokentype.metalinguistic in x.token_type]])
		ret["tot tokens-pause"] += len([x for x in unit.tokens.values() if df.tokentype.shortpause in x.token_type])
		ret["tot tokens-err"] += len([x for x in unit.tokens.values() if df.tokentype.error in x.token_type])

	ret["overlaps"] = transcript.overlap_events
	ret["TUs"] = sum(1 for x in transcript.transcription_units if x.include)
	ret["removed TUs"] = sum(1 for x in transcript.transcription_units if not x.include)

	ret["WARNINGS"] = {}
	ret["ERRORS"] = {}
	# ret["ERRORS SPECS"] = {}

	for unit in transcript:
		for key, value in unit.warnings.items():
			if not key in ret["WARNINGS"]:
				ret["WARNINGS"][key] = 0
			ret["WARNINGS"][key] += value

	for unit in transcript:
		for key, value in unit.errors.items():
			if not key in ret["ERRORS"]:
				# ret["ERRORS SPECS"][key] = []
				ret["ERRORS"][key] = 0
			if value:
				# ret["ERRORS SPECS"][key].append(unit.tu_id)
				ret["ERRORS"][key] += 1

	return ret


if __name__ == "__main__":
	conll2conllu("/home/ludop/Documents/TREEBANK/kiparla-treebank/dati/current_tagged/BOA3017.conll", "./prova.txt")
	# csv2eaf("/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.tsv", "/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.eaf")