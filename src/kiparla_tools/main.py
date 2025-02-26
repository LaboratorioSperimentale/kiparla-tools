import kiparla_tools.data as data
import kiparla_tools.serialize as serialize
import kiparla_tools.alignment as alignment
import pandas as pd
import os


def process_transcript(filename, annotations_filename, duration_threshold = 0.1):
	"""
	The function `process_transcript` reads a CSV file containing transcript data, creates transcription
	units, tokenizes them, and adds token features before returning the processed transcript.

	:param filename: name of the file that contains the transcript data to be processed.
	It is expected to be a file path pointing to the transcript file
	:param duration_threshold: minimum duration threshold for identifying overlapping transcription units in
	the transcript. If the duration of overlap between two transcription units is greater than or equal
	to the `duration_threshold`, they are considered as overlapping.
	:return: processed transcript object.
	"""

	ignore_overlaps = open(annotations_filename, encoding="utf-8").readlines()
	ignore_overlaps = [line.strip().split() for line in ignore_overlaps]

	transcript_name = filename.stem
	transcript = data.Transcript(transcript_name)

	for tu_id, speaker, start, end, duration, annotation in serialize.read_csv(filename):
		new_tu = data.TranscriptionUnit(tu_id, speaker, start, end, duration, annotation)
		transcript.add(new_tu)

	transcript.sort()
	transcript.find_overlaps(duration_threshold=duration_threshold)

	for tu in transcript:
		tu.tokenize()

	transcript.check_overlaps()

	for tu in transcript:
		tu.add_token_features()

	return transcript


def align_transcripts(transcripts_dict, output_folder):
	for i, t_a in enumerate(list(transcripts_dict.keys())[:-1]):
		t_a_name = t_a.split("_")[1]
		for t_b in list(transcripts_dict.keys())[i+1:]:
			t_b_name = t_b.split("_")[1]

			if t_a_name == t_b_name:
				tokens_a, tokens_b = alignment.align_transcripts(transcripts_dict[t_a],
																transcripts_dict[t_b])

				serialize.print_aligned(tokens_a, tokens_b, output_folder.joinpath(f"{t_a}_{t_b}.tsv"))


# Funzione che apre tutti i file transcript e genera un file di output per ognuno
def process_all_transcripts(input_dir="data/csv_puliti", output_dir="data/output"):
	transcripts_dict = {}

	if not os.path.exists(output_dir): # non abbiamo cartella di output, quindi la creiamo
		os.makedirs(output_dir)

	# Iterare attraverso tutti i file .csv
	for filename in os.listdir(input_dir):
		if filename.endswith(".csv"):
			transcript_name = filename.replace(".csv", "") # rimuove .csv (prendendo come esempio 01_ParlaBOA_E)
			transcript = data.Transcript(transcript_name)

			file_path = os.path.join(input_dir, filename)
			print(f"Processing {filename}")

			for tu_id, speaker, start, end, duration, annotation in serialize.read_csv(file_path):
				new_tu = data.TranscriptionUnit(tu_id, speaker, start, end, duration, annotation)
				transcript.add(new_tu)

			transcript.sort()
			transcript.find_overlaps(duration_threshold=0.1)

			for tu in transcript:
				tu.tokenize()

			transcript.check_overlaps()

			for tu in transcript:
				tu.add_token_features()

			output_filename = os.path.join(output_dir,f"{transcript_name}.conll")
			serialize.conversation_to_conll(transcript, output_filename)
			serialize.conversation_to_linear(transcript, os.path.join(output_dir,f"{transcript_name}.tsv"))
			transcripts_dict[transcript_name] = transcript

	return transcripts_dict

if __name__ == "__main__":
	import pathlib

	output_dir = 'data/alignments'
	if not os.path.exists(output_dir):
		os.makedirs(output_dir)

	transcripts = process_all_transcripts("data/csv_puliti_demo", "data/output_sample")

	for i, t_a in enumerate(list(transcripts.keys())[:-1]):
		t_a_name = t_a.split("_")[1]
		for t_b in list(transcripts.keys())[i+1:]:
			t_b_name = t_b.split("_")[1]

			if t_a_name == t_b_name:
				tokens_a, tokens_b = alignment.align_transcripts(transcripts[t_a],
																transcripts[t_b])

				serialize.print_aligned(tokens_a, tokens_b, f"data/alignments/{t_a}_{t_b}.tsv")

	for file in pathlib.Path(f"data/output_sample").glob("*.tsv"):
		serialize.csv2eaf(file, f"data/audio/{file.stem}.wav", f"data/output_sample/{file.stem}.eaf")

	serialize.print_full_statistics(transcripts, "data/output_sample/statistics.csv")
