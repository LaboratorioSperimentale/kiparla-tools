def compute_stats_per_minute(tus_list, split_size, f1_tu=lambda x: True, f2_tu=lambda x: 1):

	ret_list = []
	n_curr = 0
	i=0
	for tu in tus_list:
		if tu.end > split_size*i:
			ret_list.append(n_curr)
			i+=1
		if f1_tu(tu):
			n_curr += f2_tu(tu)

	ret_list.append(n_curr)

	return ret_list