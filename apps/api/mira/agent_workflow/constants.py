"""Static constants, month names, number-word regexes, and tour alias patterns."""

MONTHS = "January February March April May June July August September October November December".split()
ALIASES = {
    "T01": r"sigiriya.*(?:day (?:trip|tour)|from kandy)|minneriya.*day",
    "T05": r"whale|dolphin",
    "T09": r"cultural triangle|ancient cities",
    "T11": r"mirissa.*(?:beach|stay)|beach.*mirissa",
    "T04": r"galle fort.*(?:walk|tour)",
}
WORDS = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
COUNT = r"\d{1,3}|" + "|".join(WORDS[1:])
