import sys
from wtpsplit import SaT

# use our '-sm' models for general sentence segmentation tasks

text = []
file = open(sys.argv[1]).readlines()

for line in file[1:]:
	token = line.strip().split("\t")[3]
	if not token.startswith("{") and not "~" in token:
		text.append(token)
	# input()

# print(text)


sat_sm = SaT("sat-12l")
ret = sat_sm.split(" ".join(text))
# returns ["this is a test ", "this is another test"]
print("\n".join(ret))
