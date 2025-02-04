import csv
import regex as re
from ast import literal_eval
from kiparla_tools import data as d
from kiparla_tools import dataflags as df
import pandas as pd
from speach import elan
from pympi import Elan as EL

# Creating a file that contains statistics for each transcript
def print_full_statistics(list_of_transcripts, output_filename):
	
	max_columns = 0
	full_statistics = [] # list that contains all transcripts
	for transcript_id, transcript in list_of_transcripts.items(): # iterating each transcript
		transcript.get_stats () # calculating statistics
		stats_dict = transcript.statistics.set_index("Statistic")["Value"].to_dict() # converting statistics into a dictionary
		if len(stats_dict["num_tu"]) > max_columns:
			max_columns = len(stats_dict["num_tu"])
		# print(stats_dict)
		# input()
		# stats_dict["Transcript_ID"] = transcript.tr_id	# adding the transcript id
		full_statistics.append(stats_dict)

	for stats in full_statistics:
		for el in range(max_columns):
			stats[f"num_tu::{el}"] = stats["num_tu"][el] if len(stats["num_tu"])>el else 0

		del stats["num_tu"]
		# data_for_df = []
		# for transcript_id, data in stats.items():
		# 	full_df_data = {
        # 		# "Transcript_ID": data["transcript_id"],
        # 		"Transcript_ID": transcript_id,
        # 		"num_speakers": data["num_speakers"],
        # 		"num_tu": data["num_tu"],
        # 		"num_total_tokens": data["num_total_tokens"],
        # 		"average_duration": data["average_duration"],
        # 		# "num_turns": data["num_turns"],
        # 		"annotator": data["annotator"],
        # 		"reviewer": data["reviewer"],
        # 		"transcription_type": data["transcription_type"],
       	# 		"expertise": data["expertise"],
        # 		"accuracy": data["accuracy"],
        # 		"minutes_experience": data["minutes_experience"],
		# 		"sec30": data["sec30"],
		# 		"sec60": data["sec60"],
		# 		"sec90": data["sec90"],
		# 		"sec120": data["sec120"],
		# 		"sec_assignment": data["sec_assignment"],
    	# 	}

	# Creating a df with all statistics
	statistics_complete = pd.DataFrame(full_statistics) # creating the dataframe
	statistics_complete.to_csv(output_filename, index=False, sep="\t") # converting the df to csv


def conversation_to_csv(transcript, output_filename, sep = '\t'):

	with open(output_filename, "w", encoding="utf-8") as fout:

		for turn_id, turn in enumerate(transcript.turns):
			turn_speaker = turn.speaker
			# turn_id = None
			for tu_id in turn.transcription_units_ids:
				# print(tu_id)
				transcription_unit = transcript.transcription_units_dict[tu_id]
				# print(transcription_unit)
				tu_start = transcription_unit.start
				tu_end = transcription_unit.end
				# print(transcription_unit.tokens)

				for token_id, token in transcription_unit.tokens.items():

					infos = [str(turn_id),
							str(tu_id),
							turn_speaker,
							str(token_id+1),
							token.token_type.name,
							token.text,
							token.orig_text,
							str(tu_start) if token_id==0 else "_",
							str(tu_end) if token_id == len(transcription_unit.tokens)-1 else "_",
							token.intonation_pattern.name if token.intonation_pattern else "_",
							token.position_in_tu.name if token.position_in_tu else "_",
							# token.pace,
							# token.volume,
							# str(token.prolongations),
							# "|".join(token.prolonged_sounds),
							# token.interrupted,
							# token.guess,
							# token.overlap
							]

					print(sep.join(infos), file=fout)


def conversation_to_conll(transcript, output_filename, sep = '\t'):
	fieldnames = ["speaker", "tu_id", "token", "orig_token", "span",
				"type", "metalinguistic_category", "align", "intonation", "unknown", "interruption", "truncation",
				"prosodicLink", "spaceafter", "prolongations", "slow_pace", "fast_pace",
				"volume", "guesses", "overlaps"]

	with open(output_filename, "w", encoding="utf-8", newline='') as fout:
		writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=sep, restval="_")
		writer.writeheader()

		for turn_id, turn in enumerate(transcript.turns):
			turn_speaker = turn.speaker
			for tu_id in turn.transcription_units_ids:
				tu = transcript.transcription_units_dict[tu_id]

				for tok_id, tok in tu.tokens.items():

					to_write = {"speaker": tu.speaker,
								"tu_id": tu_id,
								"token": tok.text,
								"orig_token": tok.orig_text,
								"type": tok.token_type.name,
								"intonation": tok.intonation_pattern.name if tok.intonation_pattern else "_",
								"interruption": "Interrupted=Yes" if tok.interruption else "_",
								"truncation": "Truncated=Yes" if tok.truncation else "_",
								"unknown": "Unknown=Yes" if tok.unknown else "_",
								"prosodicLink": "ProsodicLink=Yes" if tok.prosodiclink else "_",
								"spaceafter": "SpaceAfter=No" if not tok.spaceafter else "_"
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
				"W:normalized_spaces", "W:numbers", "W:accents", "W:non_jefferson", "W:pauses_trim", "W:prosodic_trim", "W:moved_boundaries",
				"E:volume", "E:pace", "E:guess", "E:overlap", "E:overlap_mismatch",
				"E:overlap_duration",
				"T:shortpauses", "T:metalinguistic", "T:errors", "T:linguistic",
				"annotation", "correct", "text"]

	with open(output_filename, "w", encoding="utf-8") as fout:
		writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=sep, restval="_")
		writer.writeheader()

		for turn_id, turn in enumerate(transcript.turns):
			turn_speaker = turn.speaker
			for tu_id in turn.transcription_units_ids:
				tu = transcript.transcription_units_dict[tu_id]

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
							"E:volume": tu.errors["UNBALANCED_DOTS"],
							"E:pace": tu.errors["UNBALANCED_PACE"],
							"E:guess": tu.errors["UNBALANCED_GUESS"],
							"E:overlap": tu.errors["UNBALANCED_OVERLAP"],
							"E:overlap_mismatch": tu.errors["MISMATCHING_OVERLAPS"],
							"T:shortpauses": sum([df.tokentype.shortpause in tok.token_type for _, tok in tu.tokens.items()]),
							"T:metalinguistic": sum([df.tokentype.metalinguistic in tok.token_type for _, tok in tu.tokens.items()]),
							"T:errors": sum([df.tokentype.error in tok.token_type for _, tok in tu.tokens.items()]),
							"T:linguistic": sum([df.tokentype.linguistic in tok.token_type for _, tok in tu.tokens.items()])}

				if len(tu.overlap_duration) > 0:
					overlaps = []
					for unit_id, duration in tu.overlap_duration.items():
						overlaps.append(f"{unit_id}={duration:.3f}")

					to_write["E:overlap_duration"] = ",".join(overlaps)
					# overlapping_units = []
					# for x, y in tu.overlapping_times.items():
					# 	x = [str(el) for el in x]
					# 	overlapping_units.append("+".join(x))
					# to_write["overlapping_units"] = ",".join(overlapping_units)
					# print(tu.overlapping_spans)
					# print(tu.overlapping_times)
					# input()

				writer.writerow(to_write)


def csv2eaf(input_filename, output_filename, sep="\t"):

	tus = []
	tiers = set()
	with open(input_filename, encoding="utf-8") as csvfile:
		reader = csv.DictReader(csvfile, delimiter='\t')
		for row in reader:
			tiers.add(row["speaker"])
			tus.append(row)

	doc = EL.Eaf(author="automatic_pipeline")

	for tier_id in tiers:
		doc.add_tier(tier_id=tier_id)

	for annotation in tus:
		if literal_eval(annotation["include"]):
			doc.add_annotation(id_tier = annotation["speaker"],
							start=int(float(annotation["start"])*1000),
							end=int(float(annotation["end"])*1000),
							value=f"id:{annotation['tu_id']} {annotation['correct']}"
							)
	doc.to_file(output_filename)


def eaf2csv(input_filename, output_filename, sep="\t"):

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
						"text": re.sub(r"^id:[0-9]+", "", anno.value.strip())
						}
			full_file.append(to_write)

	full_file = sorted(full_file, key=lambda x: float(x["start"]))

	with open(output_filename, "w", encoding="utf-8", newline='') as fout:
		writer = csv.DictWriter(fout, fieldnames=fieldnames, delimiter=sep)
		writer.writeheader()

		for el_no, to_write in enumerate(full_file):
			to_write["tu_id"] = el_no
			writer.writerow(to_write)


def read_csv(input_filename):

	with open(input_filename, encoding="utf-8", newline='') as csvfile:
		reader = csv.DictReader(csvfile, delimiter="\t")

		for row in reader:
			yield int(row["tu_id"]), row["speaker"], float(row["start"]), float(row["end"]), float(row["duration"]), row["text"]


if __name__ == "__main__":
	eaf2csv("/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.eaf", "/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.csv")
	# csv2eaf("/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.tsv", "/home/ludop/Documents/kiparla-treebank/dati/output/BOA3017.eaf")