"""
Shared grammar constants for subtitle segmentation.
Single source of truth for grammar rule sets used by both RuleSegmenter and LLMSegmenter.
"""

# Articles
ARTICLES = {"a", "an", "the"}

# Determiners
DETERMINERS = {
    "my", "your", "his", "her", "its", "our", "their",
    "this", "that", "these", "those",
    "each", "every", "some", "any", "no",
}

# Subjects / Pronouns
SUBJECTS = {
    "i", "you", "he", "she", "it", "we", "they",
    "there", "here", "who", "which",
}

# Auxiliary / Modal verbs
AUXILIARIES = {
    "am", "is", "are", "was", "were", "be", "been", "being",
    "has", "have", "had",
    "do", "does", "did",
    "can", "could", "shall", "should", "will", "would",
    "may", "might", "must",
    "ought", "need", "dare", "used",
    "having", "going",
    # Contractions
    "re", "ve", "ll", "d", "m",
}

# Prepositions
PREPOSITIONS = {
    "in", "on", "at", "by", "with", "from", "of", "to", "for",
    "into", "onto", "off", "about", "around", "out", "up", "down",
    "over", "under", "between", "through", "across",
    "during", "before", "after", "upon", "without",
    "as", "like", "per",
}

# Conjunctions / clause starters
CONJUNCTIONS = {
    "and", "but", "or", "so",
    "because", "if", "when", "while", "though", "although", "than",
    "as", "that", "which", "who", "whose", "whom",
    "yet", "nor", "where", "unless", "since",
}

# Negations
NEGATIONS = {"not", "never", "no"}
