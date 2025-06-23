from enum import Flag, auto

class position(Flag):
	start = auto()
	end = auto()
	inner = auto()

class intonation(Flag):
	plain = auto()
	weakly_rising = auto()
	falling = auto()
	rising = auto()

class pace(Flag):
	fast = auto()
	slow = auto()

class volume(Flag):
	high = auto()
	low = auto()


class tokentype(Flag):
	linguistic = auto()
	shortpause = auto()
	nonverbalbehavior = auto()
	error = auto()
	unknown = auto()
	anonymized = auto()


class languagevariation(Flag):
	none = auto()
	some = auto()
	all = auto()