from typing import List, Dict, Any

def search_keyword(transcript_data: Dict[str, Any], keyword: str) -> List[Dict[str, Any]]:
    """
    Search for a keyword in the transcript data and return occurrences with context.
    
    Args:
        transcript_data: Dictionary containing "words" list or "transcript" string.
                         Expected structure: {"words": [{"word": "...", "start": 0.0, "end": 0.0}, ...]}
        keyword: The word or phrase to search for.
        
    Returns:
        List of dictionaries containing:
            - occurrence: Index of occurrence (1-based)
            - word: Matched word(s)
            - timestamp: Start time of the match
            - context: 20 words before and after
            - start_time: Start time of the match
            - end_time: End time of the match
    """
    words = transcript_data.get("words", [])
    
    # Validation
    if not words or not keyword:
        return []

    keyword_lower = keyword.lower()
    results = []
    
    occurrence_count = 0

    # Iterate through words to find matches
    # Note: This simple iteration handles single-word keywords. 
    # For multi-word phrases, we would need a sliding window, but the requirement implies "word" logic generally.
    # We'll implement partial matching on single words as requested ("run" finds "running").
    
    for i, word_item in enumerate(words):
        # Handle various key names just in case (Whisper uses 'word', Gemini might vary)
        text = word_item.get("word", "") or word_item.get("text", "")
        
        # Partial match check
        if keyword_lower in text.lower():
            occurrence_count += 1
            
            # Context window indices (20 words before, 20 after)
            start_idx = max(0, i - 20)
            end_idx = min(len(words), i + 21) # +1 for inclusive of current word, +20 context
            
            # Extract context text
            context_words = [
                w.get("word", "") or w.get("text", "") 
                for w in words[start_idx:end_idx]
            ]
            context_str = " ".join(context_words)
            
            results.append({
                "occurrence": occurrence_count,
                "word": text,
                "timestamp": word_item["start"],
                "context": context_str,
                "start_time": word_item["start"],
                "end_time": word_item["end"]
            })
            
    return results

if __name__ == "__main__":
    # Test Cases
    sample_data = {
        "words": [
            {"word": "The", "start": 1.0, "end": 1.2},
            {"word": "quick", "start": 1.2, "end": 1.5},
            {"word": "brown", "start": 1.5, "end": 1.8},
            {"word": "fox", "start": 1.8, "end": 2.0},
            {"word": "jumps", "start": 2.0, "end": 2.5},
            {"word": "over", "start": 2.5, "end": 2.8},
            {"word": "the", "start": 2.8, "end": 3.0},
            {"word": "lazy", "start": 3.0, "end": 3.5},
            {"word": "dog", "start": 3.5, "end": 4.0},
            # ... imagine more words for context testing
        ]
    }
    
    print("Testing 'fox':")
    print(search_keyword(sample_data, "fox"))
    
    print("\nTesting 'jumps' (partial 'jump'):")
    print(search_keyword(sample_data, "jump"))
    
    print("\nTesting 'cat' (not found):")
    print(search_keyword(sample_data, "cat"))
