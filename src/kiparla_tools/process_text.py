import regex as re
import num2words

def remove_spaces(transcription):
	tot_subs = 0

	new_string, subs_made = re.subn(r"\t+", "", transcription)
	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	# removing newlines
	new_string, subs_made = re.subn(r"\n+", "", transcription)
	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	# removing double spaces
	new_string, subs_made = re.subn(r"\s\s+", " ", transcription)
	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	return tot_subs, transcription.strip()

# transform "pò" into "po'" (keep count)
def replace_po(transcription):
	tot_subs = 0
	new_string, subs_made = re.subn(r"\bp([^ =]*)ò\b", r"p\1o'", transcription)

	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	return tot_subs, transcription.strip()

# transform "chè" into "ché" (keep count)
# TODO: fix it to handle also pero'>però, perche'>perché and stuff like this
def replace_che(transcription):

	words_to_replace = {"perchè", "benchè", "finchè", "poichè", "anzichè", "dopodichè", "granchè",
						"fourchè", "affinchè", "pressochè"}

	tot_subs = 0

	for word in words_to_replace:

		new_word = f"\\b{word[0]}"
		sub_word = f"{word[0]}"
		for char_id, char in enumerate(word[1:]):
			new_word += "([^ =]*)" + char
			sub_word = sub_word + "\\" + str(char_id+1) + char
		new_word += "\\b"

		sub_word = sub_word[:-1] + "é"

		# print(new_word, sub_word)

		new_word = re.compile(new_word)
		new_string, subs_made = re.subn(new_word, rf"{sub_word}", transcription)

		if subs_made > 0:
			tot_subs += subs_made
			transcription = new_string
		# sub_word = re.compile(sub_word)
	return tot_subs, transcription

	# regex = r"\b(perchè|benchè|finchè|poichè|anzichè|dopodichè|granchè|fuorchè|affinchè|pressochè)\b"
	# # chè > ché
	# new_string, subs_made = re.subn(regex, lambda m: m.group(0).replace("è", "é"), transcription)

	# if subs_made > 0:
	# 	tot_subs += subs_made
	# 	transcription = new_string

	# return tot_subs, transcription.strip()


# remove initial and final pauses (keep count)
def remove_pauses(transcription):
	tot_subs = 0
	new_string, subs_made = re.subn(r"^([\[\]()<>°]?)\s*\{P\}\s*|\s*\{P\}\s*([\[\]()<>°]?)$",
									r"\1\2",
									transcription)

	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	return tot_subs, transcription.strip()

def overlap_prolongations(transcription):
	tot_subs = 0

	new_string, subs_made = re.subn(r"(\w:*)\[:",
									r"[\1:",
									transcription)

	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	return tot_subs, transcription


# remove symbols that are not part of jefferson (keep count)
# TODO: numeri?
def clean_non_jefferson_symbols(transcription):
	tot_subs = 0
	new_string, subs_made = re.subn(r"[^{}_,\?.:=°><\[\]\(\)\w\s'\-~$#]",
									"",
									transcription) # keeping also the apostrophe, # and $

	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	return tot_subs, transcription.strip()

# correct unbalanced °° (must be even)
def check_even_dots(transcription):
	even_dots_count = transcription.count ("°")

	if even_dots_count % 2 == 0:
		return True
	else:
		return False

def check_normal_parentheses(annotation, open_char, close_char):
	isopen = False
	# count = 0
	for char in annotation:
		if char == open_char:
			if isopen:
				return False
			else:
				isopen = True
			# count += 1
		elif char == close_char:
			if isopen:
				isopen = False
			else:
				return False

	return isopen is False

def check_angular_parentheses(annotation):

	fastsequence = False   # >....<
	slowsequence = False    # <.....>
	for char in annotation:
		if char == "<":
			if fastsequence:
				fastsequence = False
			elif not slowsequence:
				slowsequence = True

		elif char == ">":
			if slowsequence:
				slowsequence = False
			elif not fastsequence:
				fastsequence = True

	if fastsequence or slowsequence:
		return False
	return True

def check_spaces(transcription):

	tot_subs = 0

	# "[ ([^ ])" -> [$1
	new_string, subs_made = re.subn(r"([\[\(]) ([^ ])", r"\1\2", transcription)
	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	# "([^ ]) ]" -> $1]
	new_string, subs_made = re.subn(r"([^ ]) ([\)\]])", r"\1\2", transcription)
	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	# "[^ ] [.,:?]" -> $1$2
	new_string, subs_made = re.subn(r"([^ ]) ([.,:?])", r"\1\2", transcription)
	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	# "[^ \[\(<>°](.)" -> $1 (.)
	new_string, subs_made = re.subn(r"([^ \[\(<>°])(\{[^}]+\})", r"\1 \2", transcription)
	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	# "(.)[^ \]]" -> (.) $1
	new_string, subs_made = re.subn(r"(\{[^}]+\})([^ \]\)<>°])", r"\1 \2", transcription)
	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	return tot_subs, transcription.strip()

def check_spaces_dots(transcription):
	matches = re.split(r"(°[^°]+°)", transcription)
	matches = [x for x in matches if len(x)>0]
	subs = 0
	if len(matches)>0:
		for match_no, match in enumerate(matches):
			if match[0] == "°":
				if match[1] == " ":
					match = match[0]+match[2:]
					subs += 1
				if match[-2] == " ":
					match = match[:-2]+match[-1]
					subs += 1
				matches[match_no] = match
		transcription = "".join(matches)

	return subs, transcription.strip()

def check_spaces_angular(transcription):

	matches = []

	fastsequence = False   # >....<
	slowsequence = False    # <.....>

	cur_split = []
	for char in transcription:
		if char == "<":
			if fastsequence:
				cur_split.append(char)
				matches.append(cur_split)
				cur_split = []
				fastsequence = False
			elif not slowsequence:
				matches.append(cur_split)
				cur_split = []
				cur_split.append(char)
				slowsequence = True

		elif char == ">":
			if slowsequence:
				cur_split.append(char)
				matches.append(cur_split)
				cur_split = []
				slowsequence = False
			elif not fastsequence:
				matches.append(cur_split)
				cur_split = []
				cur_split.append(char)
				fastsequence = True

		else:
			cur_split.append(char)

	if len(cur_split) > 0:
		matches.append(cur_split)

	matches = ["".join(x) for x in matches if len(x)>0]

	subs = 0
	if len(matches)>0:
		for match_no, match in enumerate(matches):
			if match[0] in [">", "<"]:
				if match[1] == " ":
					match = match[0]+match[2:]
					subs += 1
					# print(subs)
				if match[-2] == " ":
					match = match[:-2]+match[-1]
					subs += 1
					# print(subs)
				matches[match_no] = match
		transcription = "".join(matches)

	return subs, transcription.strip()


def check_numbers(transcription):

	matches = list(re.finditer(r"\b[0-9]+\b", transcription))
	spans = [match.span() for match in matches]

	if len(spans) == 0:
		return 0, transcription


	shifted_spans = [(0, spans[0][0])]
	if len(spans) > 1:
		i=0
		j=1
		while j < len(spans):
			shifted_spans.append((spans[i][1], spans[j][0]))
			i+=1
			j+=1
	shifted_spans.append((spans[-1][1], len(transcription)))

	translations = []
	for match in matches:
		sub = num2words.num2words(match.group(0), lang="it")
		if sub.endswith("tre") and len(sub)>3:
			sub = sub[:-1]+"é"
		translations.append(sub)

	i=0
	new_transcription = ""
	while i<len(translations):
		new_transcription+=transcription[shifted_spans[i][0]:shifted_spans[i][1]]
		new_transcription+=translations[i]
		i+=1

	new_transcription+=transcription[shifted_spans[i][0]:shifted_spans[i][1]]

	return len(matches), new_transcription


def replace_spaces(match):
	return '{' + match.group(1).replace(' ', '_') + '}'

def meta_tag(transcription):
	subs_map = {"((": "{",
				"))": "}",
				"(.)": "{P}"}

	for old_string, new_string in subs_map.items():
		sub_annotation, subs_made = re.subn(re.escape(old_string), new_string, transcription)
		transcription = sub_annotation

		# replace spaces with _ in comments
		transcription = re.sub(r"\{([\w ]+)\}", replace_spaces, transcription)

	return transcription


def remove_prosodiclinks(transcription):
	tot_subs = 0
	new_string, subs_made = re.subn(r"^([\[\]()<>°]?)\s*=\s*|\s*=\s*([\[\]()<>°]?)$",
									r"\1\2",
									transcription)

	if subs_made > 0:
		tot_subs += subs_made
		transcription = new_string

	return tot_subs, transcription.strip()

def check_dialect_sign(transcription):
	if transcription[0] == "#":
		return transcription[1:], True
	return transcription, False

def check_x(transcription):
	if 'x' in transcription:
		return "unkown"

if __name__ == "__main__":
	print(overlap_prolongations("questo:[::]"))