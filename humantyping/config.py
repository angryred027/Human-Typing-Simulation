# Typing model configuration

# Default average typing speed (words per minute)
DEFAULT_WPM = 60
WPM_STD = 10  # WPM standard deviation

# Average word length (standard)
AVG_WORD_LENGTH = 5

# Probabilities
PROB_ERROR = 0.04
PROB_SWAP_ERROR = 0.015
PROB_NOTICE_ERROR = 0.85

# Correction probabilities
DRIFT_CORRECTION_PROB = 0.8  # Probability to notice error at distance >= 2

# Error multipliers by context
COMPLEX_WORD_ERROR_MULT = 1.5
COMMON_WORD_ERROR_MULT = 0.5
COMPOSED_ACCENT_ERROR_MULT = 2.0

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

# Floor values for time samples
MIN_KEYSTROKE_TIME = 0.02
MIN_REACTION_TIME = 0.1
MIN_BACKSPACE_TIME = 0.03

# Specific penalties
TIME_DIRECT_ACCENT_PENALTY = 0.15
TIME_COMPOSED_ACCENT_PENALTY = 0.4
TIME_UPPERCASE_PENALTY = 0.2
TIME_SPACE_PAUSE_MEAN = 0.25
TIME_SPACE_PAUSE_STD = 0.05

# Fatigue
FATIGUE_FACTOR = 1.0005
FATIGUE_CAP = 1.5  # Maximum fatigue multiplier
