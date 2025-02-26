"""Command Line Interface for the toolkit"""
import argparse
import tqdm
import pathlib

import spacy_udpipe
from wtpsplit import SaT

from kiparla_tools import args_check as ac
from kiparla_tools import serialize
from kiparla_tools import main as main_tools
from kiparla_tools import linguistic_pipeline as pipeline

def _eaf2csv(args):
	input_files = []
	if args.input_dir:
		input_files = args.input_dir.glob("*.eaf")
	else:
		input_files = args.input_files

	if args.units_annotations_dir:
		annotations_fpaths = {}
		for file in input_files:
			supposed_annotation_path = pathlib.Path(args.units_annotations_dir).joinpath(f"{file.stem}.txt")
			if supposed_annotation_path.is_file():
				annotations_fpaths[file.stem] = supposed_annotation_path

	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		output_fname = args.output_dir.joinpath(f"{filename.stem}.csv")
		serialize.eaf2csv(filename, output_fname, annotations_fpaths[filename.stem])


def _csv2eaf(args):
	input_files = []
	if args.input_dir:
		input_files = args.input_dir.glob("*.csv")
	else:
		input_files = args.input_files

	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		basename = filename.stem
		if basename.endswith(".tus"):
			basename = basename[:-4]
		output_fname = args.output_dir.joinpath(f"{basename}.eaf")
		audio_fname = args.audio_dir.joinpath(f"{basename}.wav")
		serialize.csv2eaf(filename, str(audio_fname), output_fname,
						args.delimiter, args.multiplier_factor,
						args.include_ids)


def _process(args):
	input_files = []
	if args.input_dir:
		input_files = args.input_dir.glob("*.csv")
	else:
		input_files = args.input_files

	if args.units_annotations_dir:
		annotations_fpaths = {}
		for file in input_files:
			supposed_annotation_path = pathlib.Path(args.units_annotations_dir).joinpath(f"{file.stem}.txt")
			if supposed_annotation_path.is_file():
				annotations_fpaths[file.stem] = supposed_annotation_path

	transcripts = {}
	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		transcript_name = filename.stem
		transcript = main_tools.process_transcript(filename, annotations_fpaths[filename.stem])
		transcripts[transcript_name] = transcript

		output_filename_vert = args.output_dir.joinpath(f"{transcript_name}.conll")
		output_filename_tus = args.output_dir.joinpath(f"{transcript_name}.tus.csv")
		serialize.conversation_to_conll(transcript, output_filename_vert)
		serialize.conversation_to_linear(transcript, output_filename_tus)

	if args.produce_stats:
		serialize.print_full_statistics(transcripts, args.output_dir.joinpath("stats.csv"))


def _align(args):
	input_files = []
	if args.input_dir:
		input_files = args.input_dir.glob("*.tus.csv")
	else:
		input_files = args.input_files

	transcripts = {}
	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		transcript_name = filename.stem
		transcript = serialize.transcript_from_csv(filename)

		transcripts[transcript_name] = transcript

	main_tools.align_transcripts(transcripts, args.output_dir)


def _cicle(args):

	# STEP1 eaf -> csv
	input_files = args.eaf_dir.glob("*.eaf")

	pbar = tqdm.tqdm(input_files)
	for filename in pbar:
		pbar.set_description(f"Processing {filename.stem}")
		output_fname = args.csv_dir.joinpath(f"{filename.stem}.csv")
		serialize.eaf2csv(filename, output_fname)


	input_files = args.csv_dir.glob("*.csv")
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

	input_files = args.output_dir.glob("*.csv")
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
		input_files = args.input_dir.glob("*.conll")
	else:
		input_files = args.input_files

	sat_sm = SaT("sat-12l-sm")

	nlp = spacy_udpipe.load_from_path(lang="it",
                                path="/home/ludop/Downloads/italian-postwita-ud-2.5-191206.udpipe",
                                meta={"description": "Custom 'it' model"})

	for filename in input_files:
		basename = filename.stem
		output_fname = args.output_dir.joinpath(f"{basename}.txt")

		pipeline.segment(sat_sm, nlp, filename, output_fname, args.remove_metalinguistic)



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
	parser_csv2eaf.add_argument("-a", "--audio-dir", default="audio/",
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
	parser_csv2eaf.add_argument("-i", "--include-ids", action="store_true",
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
	command_group.add_argument("--input-dir", default="input_conllu/",
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
								help="path(s) to conllu file(s)")
	command_group.add_argument("--input-dir",
								type=ac.valid_dirpath,
								help="path to input directory. All .conllu files will be transformed")
	parser_split.add_argument("-o", "--output-dir",
							type=ac.valid_dirpath,
							help="path to directory containing csv and conllu files")
	parser_split.add_argument("--remove-metalinguistic", action="store_true",
								help="") #TODO write help
	parser_split.add_argument("--annotate", action="store_true",
							help="") #TODO write help
	parser_split.add_argument("--udpipe-model", type=ac.valid_filepath,
							help="") #TODO write help
	parser_split.set_defaults(func=_segment)


	args = root_parser.parse_args()

	if "func" not in args:
		root_parser.print_usage()
		exit()

	args.func(args)

if __name__ == "__main__":
	main()