import re
import time
from collections import Counter

class RepetitionDetector:
    """
    NLP logical module to detect filler words and repetitions in incoming text.
    Maintains a sliding window in seconds to detect frequent usage.
    """
    def __init__(self, window_size=15):
        self.window_size = window_size  # How many seconds to remember past words
        self.word_history = []  # List of tuples (word, timestamp)
        
        # Common filler words and phrases
        self.filler_words = {"um", "uh", "uhh", "like", "literally", "actually", "basically"}
        self.filler_phrases = ["you know", "i mean", "at the end of the day", "sort of", "kind of"]
        
    def normalize_text(self, text):
        """Converts text to lowercase and strips punctuation."""
        text = text.lower()
        # Remove punctuation, keeping words and spaces
        text = re.sub(r'[^\w\s]', '', text)
        return text.split()
        
    def analyze(self, text):
        """
        Takes transcribed text, updates history, and returns a list of warnings.
        """
        now = time.time()
        words = self.normalize_text(text)
        warnings = []
        
        if not words:
            return warnings
            
        # 1. Immediate repetition (e.g., "like like")
        for i in range(1, len(words)):
            if words[i] == words[i-1]:
                warnings.append(f"Immediate repetition detected: '{words[i]} {words[i]}'")
                
        # 2. Filler words
        for word in words:
            if word in self.filler_words:
                warnings.append(f"Filler word detected: '{word}'")
                
        # Handle multi-word filler phrases
        text_lower = text.lower()
        for phrase in self.filler_phrases:
            if phrase in text_lower:
                warnings.append(f"Filler phrase detected: '{phrase}'")
            
        # Common structural English words to ignore for repetition tracking
        # We only want to warn on meaningful repeated nouns/verbs/adjectives
        stop_words = {"that", "this", "with", "from", "your", "what", "have", "they", "will", "would", "could", "should", "their", "there", "about", "which", "also", "going"}
            
        # 3. Frequent repetition within short window (Sliding Window logic)
        for word in words:
            # We don't count small stop words (e.g., "the", "a", "is", "in") for frequency alerts 
            # unless they are exceptionally repetitive
            if word not in self.filler_words and word not in stop_words and len(word) > 3:
                self.word_history.append((word, now))
                
        # Clean history: removing words outside the sliding window
        self.word_history = [(w, t) for w, t in self.word_history if now - t <= self.window_size]
        
        # Check current frequencies in window
        counts = Counter([w for w, t in self.word_history])
        for word, count in counts.items():
            if count >= 2:
                warnings.append(f"Frequent repetition: '{word}' used {count} times in the last {self.window_size} seconds")
                
        # Deduplicate warnings to avoid spamming the same warning multiples times in one pass
        unique_warnings = list(dict.fromkeys(warnings))
        return unique_warnings
