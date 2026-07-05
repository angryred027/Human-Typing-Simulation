# Typing model configuration

# Default average typing speed (words per minute)
DEFAULT_WPM = 60
WPM_STD = 10  # WPM standard deviation

# Average word length (standard)
AVG_WORD_LENGTH = 5


# Error probabilities.
BASE_ERROR_RATE = 0.03
PROB_ERROR = BASE_ERROR_RATE * 1.00       # XY: substitution with a neighbouring key
PROB_OMISSION = BASE_ERROR_RATE * 0.48    # OX: a letter is skipped ("major" -> "maor")
PROB_INSERTION = BASE_ERROR_RATE * 0.25   # XO: an extra neighbouring key ("this" -> "thjis")
PROB_DOUBLING = BASE_ERROR_RATE * 0.15    # DOUB12: a letter typed twice ("operation" -> "opperation")
PROB_SWAP_ERROR = BASE_ERROR_RATE * 0.10  # SWAP: two adjacent letters interchanged ("the" -> "hte")

# Case errors (Shift mistakes on letters) — correct letter, wrong case.
PROB_MISSED_SHIFT = 0.02   # uppercase intended, typed lowercase ("The" -> "the")
PROB_SHIFT_HELD = 0.01     # Shift released late after an uppercase key ("The" -> "THe")

# Correction behaviour.
PROB_NOTICE_ERROR = 0.5
DRIFT_CORRECTION_PROB = 0.7
PROB_WORD_LEVEL_CORRECTION = 0.6

# Error multipliers by context
COMPLEX_WORD_ERROR_MULT = 1.5
COMMON_WORD_ERROR_MULT = 0.1
COMPOSED_ACCENT_ERROR_MULT = 2.0
PUNCTUATION_ERROR_MULT = 2.5

# Speed factors (multipliers on keystroke time, < 1.0 = faster)
SPEED_BOOST_COMMON_WORD = 0.6
SPEED_PENALTY_COMPLEX_WORD = 1.3
SPEED_BOOST_CLOSE_KEYS = 0.5
SPEED_BOOST_BIGRAM = 0.4

# Key distance thresholds
CLOSE_KEY_THRESHOLD = 2.0
FAR_KEY_THRESHOLD = 4.0
FAR_KEY_PENALTY = 1.2

# Minimum speed multiplier to prevent unrealistic stacking of boosts
MIN_SPEED_MULTIPLIER = 0.15

# Time (in seconds)
TIME_KEYSTROKE_STD = 0.03
TIME_BACKSPACE_MEAN = 0.12
TIME_BACKSPACE_STD = 0.02
TIME_REACTION_MEAN = 0.35
TIME_REACTION_STD = 0.1
TIME_ARROW_MEAN = 0.09
TIME_ARROW_STD = 0.02

# Floor values for time samples
MIN_KEYSTROKE_TIME = 0.02
MIN_REACTION_TIME = 0.1
MIN_BACKSPACE_TIME = 0.03
MIN_ARROW_TIME = 0.03

# Specific penalties
TIME_DIRECT_ACCENT_PENALTY = 0.15
TIME_COMPOSED_ACCENT_PENALTY = 0.4
TIME_UPPERCASE_PENALTY = 0.2
TIME_SPACE_PAUSE_MEAN = 0.25
TIME_SPACE_PAUSE_STD = 0.05

# Fatigue
FATIGUE_FACTOR = 1.0005
FATIGUE_CAP = 1.5  # Maximum fatigue multiplier
