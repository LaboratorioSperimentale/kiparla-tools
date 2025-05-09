def compute_stats_per_minute(tus_list, split_size, f1_tu=lambda x: True, f2_tu=lambda x: 1):

	ret_list = []
	n_curr = 0
	i=1
	for tu in tus_list:
		if tu.end > split_size*i:
			ret_list.append(n_curr)
			i+=1
		if f1_tu(tu):
			n_curr += f2_tu(tu)

	ret_list.append(n_curr)

	return ret_list

def find_ngrams(inlist,n):
	return zip(*list(inlist[i:] for i in range(n)))

def feats2dict(s):
	return dict(el.split("=") for el in s.split("|")) if len(s)>0 and s != "_" else {}