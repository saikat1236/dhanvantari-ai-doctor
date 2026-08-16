import os
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MedicalRetriever:
    def __init__(self):
        self.kb_path = os.path.join(os.path.dirname(__file__), "medical_kb.json")
        self.kb_data: List[Dict[str, Any]] = []
        self.load_kb()

    def load_kb(self):
        try:
            if os.path.exists(self.kb_path):
                with open(self.kb_path, "r", encoding="utf-8") as f:
                    self.kb_data = json.load(f)
                logger.info(f"Loaded {len(self.kb_data)} medical guidelines from knowledge base.")
            else:
                logger.warning(f"Medical KB file not found at {self.kb_path}. Initializing empty.")
                self.kb_data = []
        except Exception as e:
            logger.error(f"Error loading medical KB: {str(e)}")
            self.kb_data = []

    def retrieve(self, query: str, limit: int = 2) -> List[Dict[str, Any]]:
        """Retrieve relevant medical guidelines based on token overlapping (BM25-style keyword matching with stopword removal)."""
        if not query or not self.kb_data:
            return []

        STOP_WORDS = {"i", "have", "had", "a", "of", "to", "in", "or", "and", "the", "my", "on", "with", "since", "for", "is", "was", "at", "an"}
        query_tokens = {t.strip("?,.!") for t in query.lower().split() if t not in STOP_WORDS}
        scored_entries = []

        for entry in self.kb_data:
            score = 0
            
            # Match against condition name (high weight)
            condition_words = [cw for cw in entry["condition"].lower().split() if cw not in STOP_WORDS]
            for cw in condition_words:
                if cw in query_tokens:
                    score += 5.0
                    
            # Match against symptoms keywords (medium weight)
            for symptom in entry.get("symptoms", []):
                # Check exact phrase match first (subtle but powerful)
                if symptom.lower() in query.lower():
                    score += 3.0
                
                # Check individual token overlap excluding stop words
                symptom_words = [sw for sw in symptom.lower().split() if sw not in STOP_WORDS]
                for sw in symptom_words:
                    if sw in query_tokens:
                        score += 1.0

            if score > 0:
                scored_entries.append((score, entry))

        # Sort by score descending
        scored_entries.sort(key=lambda x: x[0], reverse=True)
        results = [entry for score, entry in scored_entries[:limit]]
        
        logger.info(f"Retrieved {len(results)} guideline documents for query: '{query}'")
        return results
