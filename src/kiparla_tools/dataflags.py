from enum import Flag, auto

class position(Flag):
	start = auto()
	end = auto()
	inner = auto()

class intonation(Flag):
	weakly_ascending = auto()
	descending = auto()
	ascending = auto()

class pace(Flag):
	fast = auto()
	slow = auto()

class volume(Flag):
	high = auto()
	low = auto()


class tokentype(Flag):
	linguistic = auto()
	shortpause = auto()
	metalinguistic = auto()
	error = auto()
	unknown = auto()