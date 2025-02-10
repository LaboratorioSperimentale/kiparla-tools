import argparse

from kiparla_tools import args_check as ac
from kiparla_tools import serialize as serialize

def _eaf2csv(args):
	input_files = []
	if args.input_dir:
		input_files = args.input_dir.glob("*.eaf")
	else:
		input_files = args.input_files

	for filename in input_files:
		output_fname = args.output_dir.joinpath(filename.stem, ".csv")
		serialize.eaf2csv(filename, output_fname)

def _csv2eaf(args):
	input_files = []
	if args.input_dir:
		input_files = args.input_dir.glob("*.csv")
	else:
		input_files = args.input_files

	for filename in input_files:
		output_fname = args.output_dir.joinpath(filename.stem, ".eaf")
		serialize.csv2eaf(filename, output_fname)



parent_parser = argparse.ArgumentParser(add_help=False)
root_parser = argparse.ArgumentParser(prog='kiparla-tools', add_help=True)
subparsers = root_parser.add_subparsers(title="actions", dest="actions")

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
command_group.add_argument("--input-dir", default="input_eaf/",
							type=ac.valid_dirpath,
							help="path to input directory. All .eaf files will be transformed")
parser_eaf2csv.set_defaults(func=_eaf2csv)

parser_csv2eaf = subparsers.add_parser("csv2eaf", parents=[parent_parser],
										description='transform csv file into eaf',
										help='transform csv file into eaf')
parser_csv2eaf.add_argument("-o", "--output-dir", default="output_eaf/",
							type=ac.valid_dirpath,
							help="path to output directory")
group = parser_csv2eaf.add_argument_group('Input files')
command_group = group.add_mutually_exclusive_group(required=True)
command_group.add_argument("--input-files", nargs="+",
							type=ac.valid_filepath,
							help="path(s) to eaf file(s)")
command_group.add_argument("--input-dir", default="input_eaf/",
							type=ac.valid_dirpath,
							help="path to input directory. All .eaf files will be transformed")
parser_csv2eaf.set_defaults(func=_csv2eaf)

args = root_parser.parse_args()

if "func" not in args:
	root_parser.print_usage()
	exit()

args.func(args)