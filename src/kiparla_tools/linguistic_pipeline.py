import csv

import kiparla_tools.serialize as serialize
import kiparla_tools.alignment as alignment

from kiparla_tools.config_parameters import (
	CONLL_FIELDNAMES,
	MULTIWORDS
)

#TODO: move into data
def add_info(dict, spacy_tok):
	dict["id"] = spacy_tok.i + 1
	dict["lemma"] = spacy_tok.lemma_
	dict["upos"] = spacy_tok.pos_
	dict["xpos"] = spacy_tok.tag_
	dict["feats"] = str(spacy_tok.morph)
	dict["deprel"] = f"{spacy_tok.dep_}:{spacy_tok.head.i + 1}" if spacy_tok.dep_ != "ROOT" else "root:0"


def parse(model, filename, output_filename, ignore_meta):
	fieldnames = CONLL_FIELDNAMES
	final_list = []

	with open(filename, encoding="utf-8") as fin, open(output_filename, "w", encoding="utf-8") as fout:

		writer = csv.DictWriter(fout, delimiter="\t", fieldnames=fieldnames, restval="_")
		writer.writeheader()
		for unit_id, unit in serialize.units_from_conll(fin):
			unit_processed = []
			unit_text = []
			unit_full = []
			for idx, token in enumerate(unit):
				tok_type = token["type"]
				text = token["form"]
				if tok_type == "error":
					text = "E+"+text

				if ignore_meta and not tok_type in ["shortpause", "nonverbalbehavior", "error"]:
					unit_text.append(text) #TODO: handle spaceafter?
				unit_full.append(text)

			if len(unit_text):
				doc = model(" ".join(unit_text))
				# print()
				# print(doc)

				# for token in doc:
				# 	print(token.i, token, token.dep_, token.head.i, )

				doc = [token for token in doc]
				doc_text = [token.text for token in doc]

				# unit_full = il gatto ((sbadiglio)) dorme sul divano
				# unit_text = il gatto dorme sul divano
				# doc_text = il gatto dorme su il divano

				# ---> il gatto ((sbadiglio)) dorme sul su il divano

				aligned_orig, aligned_proces, _, _ = alignment.align(unit_full, doc_text)

				new_aligned_orig = []
				new_aligned_proces = []
				for a, b in zip(aligned_orig, aligned_proces):
					if (a.startswith("{") or a.startswith("E+")) and not b == "_":
						new_aligned_orig.append(a)
						new_aligned_proces.append("_")

						new_aligned_orig.append("_")
						new_aligned_proces.append(b)

					else:
						new_aligned_orig.append(a)
						new_aligned_proces.append(b)

				aligned_orig = new_aligned_orig
				aligned_proces = new_aligned_proces

				subparts = []
				i=0
				part = []
				while i<len(aligned_orig):
					while i<len(aligned_orig) and aligned_orig[i] == aligned_proces[i]:
						part.append(i)
						i+=1

					if len(part)>0:
						subparts.append(["ALIGNED", part])
						part = []

					while i<len(aligned_orig) and aligned_orig[i] != aligned_proces[i]:
						# print(aligned_orig[i], aligned_proces[i])
						part.append(i)
						i+=1

					if len(part)>0:
						subparts.append(["MISMATCH", part])
						part = []


				aligned_sequence = []

				for element in subparts:
					label, element_ids = element
					# print(label, [aligned_orig[i] for i in element_ids])
					# print(label, [aligned_proces[i] for i in element_ids])

					if label == "ALIGNED":
						for i in element_ids:
							aligned_sequence.append(("original", aligned_orig[i]))

					elif label == "MISMATCH":

						orig_elements = [aligned_orig[i] for i in element_ids if not aligned_orig[i] == "_"]
						proces_elements = [aligned_proces[i] for i in element_ids if not aligned_proces[i] == "_"]
						counts = []

						if len(orig_elements) == 0:
							for el in proces_elements:
								aligned_sequence.append(("error", el))

						for tok in orig_elements:
							if tok.startswith("{") or tok.startswith("E+"):
								counts.append(0)
							elif tok in MULTIWORDS:
								counts.append(MULTIWORDS[tok])
							elif (tok.endswith("gliene") or \
								tok.endswith("glielo") or \
								tok.endswith("gliela") or \
								tok.endswith("mene") or \
								tok.endswith("selo") or \
								tok.endswith("sela")):
								counts.append(3)
							elif tok.endswith("-") or tok.endswith("~"):
								counts.append(2)
							elif "-" in tok or "~" in tok:
								counts.append(3)
							else:
								counts.append(2)

						if len(counts) > 0:
							k=0
							while k<len(counts) and sum(counts) < len(proces_elements):
								if counts[k]>0:
									counts[k]+=1
								k+=1

							k = len(counts)-1
							while k>=0 and sum(counts) > len(proces_elements):
								if counts[k]>0:
									counts[k]-=1
								k-=1

						j=0
						for count, tok in zip(counts, orig_elements):
							if count == 0:
								# if tok.startswith("{")
								aligned_sequence.append(("nvb", tok))
								# else:
									# aligned_sequence.append(("transcription-error", tok[2:]))
							else:
								aligned_sequence.append(("multiword-B", tok))
								for _ in range(count):
									aligned_sequence.append(("multiword-I", proces_elements[j]))
									j+=1


						while len(orig_elements) > 0 and j<len(proces_elements):

							aligned_sequence.append(("error", proces_elements[j]))
							j+=1

				# print("ALIGNED SEQUENCE:")
				# print(aligned_sequence)
				# input()


				idx_unit, idx_doc = 0, 0
				last_mw_id = ""
				last_mv_idx = 0
				mw_suffix = ["a", "b", "c", "d"]
				ptr = None

				for alignment_type, token in aligned_sequence:
					# print(alignment_type, token)

					if alignment_type == "nvb":
						# print("adding", unit[idx_unit])
						unit_processed.append(unit[idx_unit])
						idx_unit += 1

					if alignment_type == "original":
						add_info(unit[idx_unit], doc[idx_doc])
						# print("adding", unit[idx_unit])
						unit_processed.append(unit[idx_unit])
						idx_unit += 1
						idx_doc += 1

					if alignment_type == "error":
						new_token = {"token_id": unit[idx_unit]["token_id"],
									"unit": unit_id,
									"form": doc[idx_doc].text}
						add_info(new_token, doc[idx_doc])
						unit_processed.append(new_token)
						# print(token)
						idx_doc += 1

					if alignment_type == "multiword-B":
						last_mw_id = unit[idx_unit]["token_id"]
						last_mv_idx = 0
						unit[idx_unit]["id"] = "100-0"
						ptr = unit[idx_unit]
						# print("adding", unit[idx_unit])
						unit_processed.append(unit[idx_unit])
						idx_unit += 1

					if alignment_type == "multiword-I":
						new_token = {"token_id": f"{last_mw_id}{mw_suffix[last_mv_idx]}",
									"unit": unit_id,
									"form": doc[idx_doc].text}
						last_mv_idx +=1
						add_info(new_token, doc[idx_doc])
						# print("adding", new_token)
						unit_processed.append(new_token)
						idx_doc += 1

						old_ids = ptr["id"].split("-")
						id_min, id_max = int(old_ids[0]), int(old_ids[1])
						curr_id = int(new_token["id"])
						if curr_id < id_min:
							id_min = curr_id
						if curr_id > id_max:
							id_max = curr_id
						ptr["id"] = f"{id_min}-{id_max}"

				# for token in unit_processed:


				root_id = -1
				ids_map = {}
				new_id = 1
				for token in unit_processed:
					token["id"] = str(token["id"])
					if not "-" in token["id"]:
						if token["id"] != "_":
							ids_map[token["id"]] = str(new_id)
						token["id"] = str(new_id)
						if token["deprel"] == "root:0":
							root_id = new_id
						new_id += 1
					# print(token["form"], ids_map)
#
				for token in unit_processed:
					# print(token["token_id"], token["id"], token["form"], token["deprel"])
					if not token["deprel"] == "root:0":
						if token["deprel"] == "_":
							token["deprel"] = "dep:" + str(root_id)
						else:
							# print("before", token["deprel"])
							token["deprel"] = ":".join([token["deprel"].rsplit(":", 1)[0], str(ids_map[token["deprel"].rsplit(":", 1)[1]])])

							# print("after", token["deprel"])
					if "-" in token["id"]:
						token["id"] = "-".join([str(ids_map[x]) for x in token["id"].split("-")])
						token["deprel"] = "_"

				final_list.extend(unit_processed)

			else:
				final_list.extend(unit)

		for token in final_list:
			if "type" in token and token["type"] == "nonverbalbehavior":
				if token["id"] == "_":
					token["id"] = token["token_id"].split("-")[1]
					token["upos"] = "X"
					token["deprel"] = "root:0"

			writer.writerow(token)


def segment(model, filename, output_filename, ignore_meta):

	full_ids = []
	full_text = []
	fieldnames = CONLL_FIELDNAMES

	with open(filename, encoding="utf-8") as fin:
		reader = csv.DictReader(fin, delimiter="\t")
		for row in reader:
			token_id = row["token_id"]
			type = row["type"]
			text = row["form"]

			if ignore_meta and not type in ["error", "shortpause", "nonverbalbehavior"]:
				full_text.append(text)
				full_ids.append(token_id)

	ret = model.split(" ".join(full_text))

	tokens = {}
	i=0
	for sent_id, sent in enumerate(ret):
		sent = sent.split()

		for tok in sent:
			tokens[full_ids[i]] = sent_id
			i += 1

	curr_token_id = 0
	with open(filename, encoding="utf-8") as fin, open(output_filename, "w", encoding="utf-8") as fout:
		reader = csv.DictReader(fin, delimiter="\t")
		writer = csv.DictWriter(fout, delimiter="\t", fieldnames=fieldnames)
		writer.writeheader()
		for row in reader:
			token_id = row["token_id"]

			if token_id in tokens:
				row["unit"] = tokens[token_id]
				curr_token_id = tokens[token_id]
			else:
				row["unit"] = curr_token_id

			writer.writerow(row)