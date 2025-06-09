"""Command Line Interface for the toolkit"""
import argparse
import tqdm
import pathlib
import collections
import logging
import json


import spacy_udpipe
import spacy_conll
import yaml
from wtpsplit import SaT

from kiparla_tools import args_check as ac
from kiparla_tools import serialize
from kiparla_tools import alignment
from kiparla_tools import main as main_tools
from kiparla_tools import linguistic_pipeline as pipeline
from kiparla_tools import logging_utils as logging_utils
from kiparla_tools import alignment

logger = logging.getLogger(__name__)
logging_utils.setup_logging(logger)


def _eaf2csv(args):
	input_files = []
	if args.input_dir:
		input_files = list(args.input_dir.glob("*.eaf"))
	else:
		input_files = list(args.input_files)

	annotations_fpaths = {}
	if args.units_annotations_dir:
		for file in input_files:
			supposed_annotation_path = pathlib.Path(args.units_annotations_dir).joinpath(f"{file.stem}.yml")
			content = {}
			if supposed_annotation_path.is_file():
				content = serialize.load_annotations(supposed_annotation_path)
			annotations_fpaths[file.stem] = content

	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		logger.info("Processing %s", filename.stem)
		output_fname = args.output_dir.joinpath(f"{filename.stem}.csv")
		annotations = {}
		if filename.stem in annotations_fpaths:
			annotations = annotations_fpaths[filename.stem]
		serialize.eaf2csv(filename, output_fname, annotations)

		if len(annotations):
			output_fname = pathlib.Path(args.units_annotations_dir).joinpath(f"{filename.stem}.yml")
			with open(output_fname, 'w', encoding="utf-8") as yaml_file:
				yaml.dump(annotations, yaml_file, indent=2)

def _csv2eaf(args):
	input_files = []
	if args.input_dir:
		input_files = list(args.input_dir.glob("*.csv"))
	else:
		input_files = list(args.input_files)

	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		logger.info("Processing %s", filename.stem)
		basename = filename.stem
		if basename.endswith(".tus"):
			basename = basename[:-4]

		output_fname = args.output_dir.joinpath(f"{basename}.eaf")
		if args.include_ids:
			output_fname = args.output_dir.joinpath(f"{basename}.ids.eaf")

		logger.info("Writing EAF output to %s", output_fname)
		audio_fname = f"{basename}.wav"
		if args.audio_dir:
			audio_fname = args.audio_dir.joinpath(f"{basename}.wav")
		serialize.csv2eaf(filename, str(audio_fname), output_fname,
						args.delimiter, args.multiplier_factor,
						args.include_ids)


def _process(args):
	input_files = []
	if args.input_dir:
		input_files = list(args.input_dir.glob("*.csv"))
	else:
		input_files = list(args.input_files)

	annotations = collections.defaultdict(dict)
	if args.units_annotations_dir:
		for file in input_files:
			supposed_annotation_path = pathlib.Path(args.units_annotations_dir).joinpath(f"{file.stem}.yml")
			if supposed_annotation_path.is_file():
				content = serialize.load_annotations(supposed_annotation_path)
				annotations[file.stem] = content

	output_json = args.output_dir.joinpath("summary.json")
	full_data = []
	transcripts = {}
	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		transcript_name = filename.stem
		pbar.set_description(f"Processing {transcript_name}")
		logger.debug("Processing %s", transcript_name)

		transcript = main_tools.process_transcript(filename, annotations[transcript_name],
												duration_threshold=args.duration_threshold)
		transcripts[transcript_name] = transcript
		logger.info("Successfully processed %s", transcript_name)

		output_filename_vert = args.output_dir.joinpath(f"{transcript_name}.conll")
		output_filename_tus = args.output_dir.joinpath(f"{transcript_name}.csv")
		logger.debug("Writing CoNLL output to %s", output_filename_vert)
		logger.debug("Writing TUs output to %s", output_filename_tus)


		full_data.append(serialize.build_json(transcript))
		serialize.conversation_to_conll(transcript, output_filename_vert)
		serialize.conversation_to_linear(transcript, output_filename_tus)

	with open(output_json, 'w', encoding="utf-8") as json_file:
		print(json.dumps(full_data, indent=2, ensure_ascii=False), file=json_file)
		# logger.info("Successfully wrote %s", output_json)

	if args.produce_stats:
		serialize.print_full_statistics(transcripts, args.output_dir.joinpath("stats.csv"))


def _align(args):


 	# caricare data_description e filtrare solo le due colonne che ci interessano
	# transcriptors_data = pd.read_csv("data/data_description.csv", sep="\t")
	# transcriptors_data["Esperto"] = transcriptors_data["Esperto"]
	# transcriptors_data["Tipo"] = transcriptors_data["Tipo"]
	# transcriptors_data["NomeFile"] = transcriptors_data["NomeFile"]

 	# # filtrare esperti
	# transcribers = transcriptors_data[
    #  (transcriptors_data["Esperto"]== "sì")
    #  (transcriptors_data["Tipo"].isin(["From-Scratch", "Whisper-Assisted"]))
	# ]

 	# # filtrare i revised escludendo quelli che terminano per _whi e e _man
	# revised = transcriptors_data[
    #     (transcriptors_data["Tipo"] == "Revised") &
    #     (~transcriptors_data["NomeFile"].str.endswith("_man")) &
    #     (~transcriptors_data["NomeFile"].str.endswith("_whi"))
    # ]

	input_files = []
	if args.input_dir:
		input_files = list(args.input_dir.glob("*.tus.csv"))
	else:
		input_files = args.input_files

	transcripts = {}
	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		transcript_name = filename.stem
		transcript = serialize.transcript_from_csv(filename)

		transcripts[transcript_name] = transcript

# impostare l'ordine trascrittore (01) / whi (20) - gold (03)
# 1. creare le coppie di file allineati in base alla tipologia di file
	pairs = []
	for t1 in transcripts:
		for t2 in transcripts:
			if t1 == t2:
				continue
			base1 = t1.split(".")[0].split("_")[1]
			base2 = t2.split(".")[0].split("_")[1]
			if base1 == base2:
				pairs.append((t1, t2))

 # 2. ordinare le coppie
	ordered_alignment = []
	for t1, t2 in pairs:
		first_num = int(t1.split("_")[0])
		second_num = int(t2.split("_")[0])
		if first_num < second_num:
			ordered = [t1, t2]
		else:
			ordered = [t2, t1]

 # 3. evitare i duplicati
		if tuple(ordered) not in ordered_alignment:
			ordered_alignment.append(tuple(ordered))
	print(ordered_alignment)
# 4. esecuxione dell'allineamento + stampa file
	for t1, t2 in tqdm.tqdm(ordered_alignment, desc="Allineamento"):
		tokens_a, tokens_b = alignment.align_transcripts(transcripts[t1], transcripts[t2])
		fout = f"{t1}_{t2}.tsv"
		output_path = pathlib.Path("data/alignments") / fout
		serialize.print_aligned(tokens_a, tokens_b, output_path)

	# main_tools.align_transcripts(transcripts, args.output_dir)


def _cicle(args):

	# STEP1 eaf -> csv
	input_files = list(args.eaf_dir.glob("*.eaf"))

	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		output_fname = args.csv_dir.joinpath(f"{filename.stem}.csv")
		serialize.eaf2csv(filename, output_fname)


	input_files = list(args.csv_dir.glob("*.csv"))
	# STEP2 process csv
	transcripts = {}
	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		transcript_name = filename.stem
		transcript = main_tools.process_transcript(filename)
		transcripts[transcript_name] = transcript

		output_filename_vert = args.output_dir.joinpath(f"{transcript_name}.conll")
		output_filename_tus = args.output_dir.joinpath(f"{transcript_name}.tus.csv")
		serialize.conversation_to_conll(transcript, output_filename_vert)
		serialize.conversation_to_linear(transcript, output_filename_tus)

	# if args.produce_stats:
	# 	serialize.print_full_statistics(transcripts, args.output_dir.joinpath("stats.csv"))

	# STEP3 csv -> eaf

	input_files = list(args.output_dir.glob("*.csv"))
	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		basename = filename.stem
		if basename.endswith(".tus"):
			basename = basename[:-4]
		output_fname = args.eaf_dir.joinpath(f"{basename}.eaf")
		# audio_fname = args.audio_dir.joinpath(f"{basename}.wav")
		serialize.csv2eaf(filename, "data/audio/PARLABOA.wav", output_fname,
						"\t", 1000, True)


def _segment(args):
	input_files = []
	if args.input_dir:
		input_files = list(args.input_dir.glob("*.conll"))
	else:
		input_files = args.input_files

	sat_sm = SaT("sat-12l-sm")

	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		basename = filename.stem
		output_fname = args.output_dir.joinpath(f"{basename}.conll")

		pipeline.segment(sat_sm, filename, output_fname, args.remove_metalinguistic)


def _parse(args):
	input_files = []
	if args.input_dir:
		input_files = list(args.input_dir.glob("*.conll"))
	else:
		input_files = args.input_files

	nlp = spacy_udpipe.load_from_path(lang="it",
								   path=args.udpipe_model,
								   meta={"description": "Custom 'it' model"})
	nlp.add_pipe("conll_formatter", last=True)
	# nlp.add_pipe("conll_formatter", last=True)

	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		basename = filename.stem
		output_fname = args.output_dir.joinpath(f"{basename}.conll")
		pipeline.parse(nlp, filename, output_fname, args.remove_metalinguistic)


def _conll2conllu(args):

	input_files = []
	if args.input_dir:
		input_files = args.input_dir.glob("*.conll")
	else:
		input_files = args.input_files

	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		basename = filename.stem
		output_fname = args.output_dir.joinpath(f"{basename}.conllu")
		serialize.conll2conllu(filename, output_fname)


def main():

	### MAIN ###
	parent_parser = argparse.ArgumentParser(add_help=False)
	root_parser = argparse.ArgumentParser(prog='kiparla-tools', add_help=True)
	subparsers = root_parser.add_subparsers(title="actions", dest="actions")

	# EAF2CSV
	parser_eaf2csv = subparsers.add_parser("eaf2csv", parents=[parent_parser],
											description='transform eaf file into csv',
											help='transform eaf file into csv')
	parser_eaf2csv.add_argument("-o", "--output-dir", default="output/",
								type=ac.valid_dirpath,
								help="path to output directory")
	group = parser_eaf2csv.add_argument_group('Input files')
	command_group = group.add_mutually_exclusive_group(required=True)
	command_group.add_argument("--input-files", nargs="+",
								type=ac.valid_filepath,
								help="path(s) to eaf file(s)")
	command_group.add_argument("--input-dir",
								type=ac.valid_dirpath,
								help="path to input directory. All .eaf files will be transformed")
	parser_eaf2csv.add_argument("--units-annotations-dir", type=ac.valid_dirpath,
								help="") #TODO: write help
	parser_eaf2csv.set_defaults(func=_eaf2csv)

	# CSV2EAF
	parser_csv2eaf = subparsers.add_parser("csv2eaf", parents=[parent_parser],
											description='transform csv file into eaf',
											help='transform csv file into eaf')
	parser_csv2eaf.add_argument("-o", "--output-dir", default="output_eaf/",
								type=ac.valid_dirpath,
								help="path to output directory")
	parser_csv2eaf.add_argument("-a", "--audio-dir",
								type=ac.valid_dirpath,
								help="path to directory containing audio files")
	group = parser_csv2eaf.add_argument_group('Input files')
	command_group = group.add_mutually_exclusive_group(required=True)
	command_group.add_argument("--input-files", nargs="+",
								type=ac.valid_filepath,
								help="path(s) to eaf file(s)")
	command_group.add_argument("--input-dir",
								type=ac.valid_dirpath,
								help="path to input directory. All .eaf files will be transformed")
	parser_csv2eaf.add_argument("-d", "--delimiter", type=str, default="\t",
								help="") #TODO: ADD HELP
	parser_csv2eaf.add_argument("-m", "--multiplier-factor", type=int, default=1000,
								help="") #TODO: ADD HELP
	parser_csv2eaf.add_argument("--include-ids", action="store_true",
								help="") #TODO write help
	parser_csv2eaf.set_defaults(func=_csv2eaf)

	# PROCESS
	parser_process = subparsers.add_parser("process", parents=[parent_parser],
											description='process transcripts',
											help='process transcripts')
	parser_process.add_argument("-o", "--output-dir", default="output_eaf/",
								type=ac.valid_dirpath,
								help="path to output directory")
	group = parser_process.add_argument_group('Input files')
	command_group = group.add_mutually_exclusive_group(required=True)
	command_group.add_argument("--input-files", nargs="+",
								type=ac.valid_filepath,
								help="path(s) to eaf file(s)")
	command_group.add_argument("--input-dir",
								type=ac.valid_dirpath,
								help="path to input directory. All .csv files will be transformed")
	parser_process.add_argument("-t", "--duration-threshold", type=float, default=0.1,
								help="") # TODO: write help
	parser_process.add_argument("-s", "--produce-stats", action="store_true",
								help="") # TODO: write help
	parser_process.add_argument("--units-annotations-dir", type=ac.valid_dirpath,
								help="") #TODO: write help
	parser_process.set_defaults(func=_process)

	# ALIGN
	parser_align = subparsers.add_parser("align", parents=[parent_parser],
										description='align transcripts',
										help='align transcripts')
	parser_align.add_argument("-o", "--output-dir", default="output_aligned/",
								type=ac.valid_dirpath,
								help="path to output directory")
	group = parser_align.add_argument_group('Input files')
	command_group = group.add_mutually_exclusive_group(required=True)
	command_group.add_argument("--input-files", nargs="+",
								type=ac.valid_filepath,
								help="path(s) to conllu file(s)")
	command_group.add_argument("--input-dir",
								type=ac.valid_dirpath,
								help="path to input directory. All .conllu files will be transformed")
	parser_align.set_defaults(func=_align)

	# CICLE
	parser_cicle = subparsers.add_parser("cicle", parents=[parent_parser],
										description='perform full transformation cicle: manually corrected eaf -> new csv -> new eaf',
										help='perform full transformation cicle')
	parser_cicle.add_argument("-e", "--eaf-dir", default="output_cicleed/",
								type=ac.valid_dirpath,
								help="path to directory containing eaf files")
	parser_cicle.add_argument("-c", "--csv-dir",
							type=ac.valid_dirpath,
							help="path to directory containing csv files")
	parser_cicle.add_argument("-o", "--output-dir",
							type=ac.valid_dirpath,
							help="path to directory containing csv and conllu files")
	parser_cicle.set_defaults(func=_cicle)

	# SPLIT
	parser_split = subparsers.add_parser("segment", parents=[parent_parser],
										description='segment into maximal units',
										help='segment into maximal units')
	group = parser_split.add_argument_group('Input files')
	command_group = group.add_mutually_exclusive_group(required=True)
	command_group.add_argument("--input-files", nargs="+",
								type=ac.valid_filepath,
								help="path(s) to conll file(s)")
	command_group.add_argument("--input-dir",
								type=ac.valid_dirpath,
								help="path to input directory. All .conll files will be transformed")
	parser_split.add_argument("-o", "--output-dir",
							type=ac.valid_dirpath,
							help="path to directory containing csv and conll files")
	parser_split.add_argument("--remove-metalinguistic", action="store_true",
								help="") #TODO write help
	parser_split.set_defaults(func=_segment)

	# PARSE
	parser_parse = subparsers.add_parser("parse", parents=[parent_parser],
										description='',
										help='')
	group = parser_parse.add_argument_group('Input files')
	command_group = group.add_mutually_exclusive_group(required=True)
	command_group.add_argument("--input-files", nargs="+",
								type=ac.valid_filepath,
								help="path(s) to conllu file(s)")
	command_group.add_argument("--input-dir",
								type=ac.valid_dirpath,
								help="path to input directory. All .conllu files will be transformed")
	parser_parse.add_argument("-o", "--output-dir",
							type=ac.valid_dirpath,
							help="path to directory containing csv and conllu files")
	parser_parse.add_argument("--remove-metalinguistic", action="store_true",
								help="") #TODO write help
	parser_parse.add_argument("--udpipe-model", #type=ac.valid_filepath,
							help="") #TODO write help
	parser_parse.set_defaults(func=_parse)

	# CONLL2CONLLU
	parser_conll2conllu = subparsers.add_parser("conll2conllu", parents=[parent_parser],
												description='',
												help='')
	group = parser_conll2conllu.add_argument_group('Input files')
	command_group = group.add_mutually_exclusive_group(required=True)
	command_group.add_argument("--input-files", nargs="+",
								type=ac.valid_filepath,
								help="path(s) to conllu file(s)")
	command_group.add_argument("--input-dir",
								type=ac.valid_dirpath,
								help="path to input directory. All .conllu files will be transformed")
	parser_conll2conllu.add_argument("-o", "--output-dir",
							type=ac.valid_dirpath,
							help="path to directory containing csv and conllu files")
	parser_conll2conllu.set_defaults(func=_conll2conllu)


	args = root_parser.parse_args()

	if "func" not in args:
		root_parser.print_usage()
		exit()

	args.func(args)

if __name__ == "__main__":
	main()