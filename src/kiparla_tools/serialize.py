import csv
import regex as re
from ast import literal_eval
import pandas as pd
from speach import elan
from pympi import Elan as EL

from kiparla_tools import data
from kiparla_tools import dataflags as df


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
		if len(stats_dict["tokens_per_minute"]) > max_columns:
			max_columns = len(stats_dict["tokens_per_minute"])
		full_statistics.append(stats_dict)

	for stats in full_statistics:
		for field in ["num_tu", "tokens_per_minute"]:
			for el in range(max_columns):
				stats[f"{field}::{el}"] = stats[f"{field}"][el] if len(stats[f"{field}"])>el else 0
			del stats[f"{field}"]

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

	fieldnames = ["token_id", "speaker", "tu_id", "token", "orig_token", "span",
				"type", "metalinguistic_category", "align", "intonation", "interruption", "truncation",
				"prosodicLink", "spaceafter", "prolongations", "slow_pace", "fast_pace",
				"volume", "guesses", "overlaps", "dialect"]

	with open(output_filename, "w", encoding="utf-8", newline='') as fout:
		writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=sep, restval="_")
		writer.writeheader()

		for tu in transcript.transcription_units:
			tu_id = tu.tu_id

			for _, tok in tu.tokens.items():

				to_write = {"token_id": tok.id,
							"speaker": tu.speaker,
							"tu_id": tu_id,
							"token": tok.text,
							"orig_token": tok.orig_text,
							"type": tok.token_type.name,
							"intonation": tok.intonation_pattern.name if tok.intonation_pattern else "_",
							"interruption": "Interrupted=Yes" if tok.interruption else "_",
							"truncation": "Truncated=Yes" if tok.truncation else "_",
							"prosodicLink": "ProsodicLink=Yes" if tok.prosodiclink else "_",
							"spaceafter": "SpaceAfter=No" if not tok.spaceafter else "_",
							"dialect": "Dialect=Yes" if tok.dialect else "_"
							}

				to_write["span"] = tu.annotation[tok.span[0]:tok.span[1]]

				align = []
				if df.position.start in tok.position_in_tu:
					align.append(("Begin", tu.start))
				if df.position.end in tok.position_in_tu:
					align.append(("End", tu.end))
				to_write["align"] = "|".join([f"{x[0]}={x[1]}" for x in align])

				to_write["prolongations"] = ",".join([f"{x[0]}x{x[1]}" for x in tok.prolongations.items()])

				slow_pace = []
				for span_id, span in tok.slow_pace.items():
					slow_pace.append(f"{span[0]}-{span[1]}({span_id})")
				to_write["slow_pace"] = ",".join(slow_pace)

				fast_pace = []
				for span_id, span in tok.fast_pace.items():
					fast_pace.append(f"{span[0]}-{span[1]}({span_id})")
				to_write["fast_pace"] = ",".join(fast_pace)

				to_write["volume"] = tok.volume.name if tok.volume else "_"

				guesses = []
				for span_id, span in tok.guesses.items():
					guesses.append(f"{span[0]}-{span[1]}({span_id})")
				to_write["guesses"] = ",".join(guesses)

				overlaps = []
				for span_id, span in tok.overlaps.items():
					overlaps.append(f"{span[0]}-{span[1]}({span_id})")
				to_write["overlaps"] = ",".join(overlaps)

				writer.writerow(to_write)


def conversation_to_linear(transcript, output_filename, sep = '\t'):

	fieldnames = ["tu_id", "speaker", "start", "end", "duration", "include",
				"W:normalized_spaces", "W:numbers", "W:accents", "W:non_jefferson", "W:pauses_trim", "W:prosodic_trim", "W:moved_boundaries", "W:switches",
				"E:volume", "E:pace", "E:guess", "E:overlap", "E:overlap_mismatch",
				"E:overlap_duration",
				"T:shortpauses", "T:metalinguistic", "T:errors", "T:linguistic",
				"annotation", "correct", "text"]

	with open(output_filename, "w", encoding="utf-8") as fout:
		writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=sep, restval="_")
		writer.writeheader()

		for tu in transcript.transcription_units:
			# tu_id = tu.tu_id

			to_write = {"tu_id": tu.tu_id,
						"speaker": tu.speaker,
						"start": tu.start,
						"end": tu.end,
						"duration": tu.duration,
						"include": tu.include,
						"annotation": tu.orig_annotation,
						"correct": tu.annotation,
						"text": " ".join(str(tok) for _, tok in tu.tokens.items()),
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
						"T:shortpauses": sum([df.tokentype.shortpause in tok.token_type for _, tok in tu.tokens.items()]),
						"T:metalinguistic": sum([df.tokentype.metalinguistic in tok.token_type for _, tok in tu.tokens.items()]),
						"T:errors": sum([df.tokentype.error in tok.token_type for _, tok in tu.tokens.items()]),
						"T:linguistic": sum([df.tokentype.linguistic in tok.token_type for _, tok in tu.tokens.items()])}


			errors = " ".join([tok.text for _, tok in tu.tokens.items() if df.tokentype.error in tok.token_type])
			to_write["T:errors"] = f"{to_write['T:errors']}, {errors}"
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
				value=f"id:{annotation['tu_id']} {annotation['correct']}"
			doc.add_annotation(id_tier = annotation["speaker"],
								start=int(float(annotation["start"])*multiplier),
								end=int(float(annotation["end"])*multiplier),
								value=value
							)
	doc.to_file(output_filename)


def eaf2csv(input_filename, output_filename, sep="\t"):
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
						"text": re.sub(r"^id:[0-9]+", "", anno.value.strip()) # TODO: substitute {} with (())
						}
			full_file.append(to_write)

	full_file = sorted(full_file, key=lambda x: float(x["start"]))

	with open(output_filename, "w", encoding="utf-8", newline='') as fout:
		writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=sep)
		writer.writeheader()

		for el_no, to_write in enumerate(full_file):
			to_write["tu_id"] = el_no
			writer.writerow(to_write)


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

if __name__ == "__main__":
	eaf2csv("/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.eaf", "/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.csv")
	# csv2eaf("/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.tsv", "/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.eaf")