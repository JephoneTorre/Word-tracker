import re
import time
from collections import Counter

class RepetitionDetector:
    """
    NLP logical module to detect filler words and repetitions in incoming text.
    Maintains a sliding window in seconds to detect frequent usage.
    """
    def __init__(self, window_size=15):
        self.window_size = window_size
        self.word_history = [] 
        
        self.filler_words = {"um", "uh", "uhh", "like", "literally", "actually", "basically"}
        self.filler_phrases = ["you know", "i mean", "at the end of the day", "sort of", "kind of"]
        
        # We only want to warn on meaningful noun/verb/adjective repeats
        self.stop_words = {"that", "this", "with", "from", "your", "what", "have", "they", "will", "would", "could", "should", "their", "there", "about", "which", "also", "going", "very", "much"}
        
    def normalize_text(self, text):
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        return text.split()
        
    def analyze(self, text):
        now = time.time()
        words = self.normalize_text(text)
        warnings = []
        
        if not words:
            return warnings
            
        # 1. Filler words / phrases
        for word in words:
            if word in self.filler_words:
                warnings.append({'word': word, 'count': 1, 'level': 'filler', 'message': f"🟡 Filler word detected: '{word}'"})
                
        text_lower = text.lower()
        for phrase in self.filler_phrases:
            if phrase in text_lower:
                warnings.append({'word': phrase, 'count': 1, 'level': 'filler', 'message': f"🟡 Filler phrase detected: '{phrase}'"})
            
        # 3. Frequent repetition within short window (Sliding Window logic)
        for word in words:
            if word not in self.filler_words and word not in self.stop_words and len(word) > 2:
                self.word_history.append((word, now))
                
        # Clean obsolete history 
        self.word_history = [(w, t) for w, t in self.word_history if now - t <= self.window_size]
        
        # Check frequencies
        counts = Counter([w for w, t in self.word_history])
        
        for word, count in counts.items(): # We must evaluate words just processed
            if count == 2 and word in words:
                warnings.append({
                    'word': word, 'count': count, 'level': 'warning', 
                    'message': f"⚠️ '{word}' repeated (2x)"
                })
            elif count == 3 and word in words:
                warnings.append({
                    'word': word, 'count': count, 'level': 'concern', 
                    'message': f"🟠 '{word}' repeated (3x)"
                })
            elif count >= 4 and word in words:
                warnings.append({
                    'word': word, 'count': count, 'level': 'critical', 
                    'message': f"🚨 '{word}' redundant ({count}x)"
                })
                
        # Deduplicate warnings
        seen = set()
        unique_warnings = []
        for w in warnings:
            # unique key by word and count, to prevent duplicates
            key = f"{w['word']}_{w['count']}"
            if key not in seen:
                seen.add(key)
                unique_warnings.append(w)
                
        return unique_warnings
