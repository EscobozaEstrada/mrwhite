#!/usr/bin/env python3
"""
Response filter to remove roleplay actions and enforce professional communication
"""
import re
import logging

logger = logging.getLogger(__name__)

# Comprehensive patterns for roleplay actions to remove
ROLEPLAY_PATTERNS = [
    # Direct action patterns at start of response
    r'^(chuckles?|smiles?|nods?|grins?|laughs?)\s+(warmly|thoughtfully|enthusiastically|gently|softly|knowingly|understandingly|approvingly|encouragingly|helpfully)\s*[,\s]*',
    
    # Asterisk actions (single and double asterisks) - COMPREHENSIVE
    r'\*[^*]+\*\s*',
    r'\*\*[^*]+\*\*\s*',
    
    # IMPROVED: More precise markdown formatting removal
    r'\*\*([^*]+?)\*\*',  # Remove **bold text** (keeps the text, removes asterisks)
    r'\*\*\s*',           # Remove ** followed by any whitespace 
    r'\*\*',              # Remove any remaining standalone **
    
    # Bullet point formatting to remove
    r'^•\s*',          # Remove bullet points at start of lines
    r'\n•\s*',         # Remove bullet points at start of new lines
    r'^\*\s+(?=\w)',   # Remove asterisk bullets like "* Something"
    r'\n\*\s+(?=\w)',  # Remove asterisk bullets on new lines
    
    # Parenthetical actions  
    r'\([^)]*(?:chuckles?|smiles?|nods?|grins?|laughs?|wags?|perks?)[^)]*\)\s*',
    
    # Descriptive action phrases
    r'(?:^|\s)(chuckles?|smiles?|nods?|grins?|laughs?)\s+(?:warmly|thoughtfully|enthusiastically|gently|softly|knowingly|understandingly|approvingly|encouragingly|helpfully)(?:\s+[^.!?]+)?[.!?]?\s*',
    
    # Common roleplay starters
    r'^(?:chuckles?|smiles?|nods?|grins?|laughs?)\s+(?:warmly|thoughtfully|enthusiastically|gently|softly|knowingly|understandingly|approvingly|encouragingly|helpfully)\s*(?:Well|Ah|Oh|I|That|Excellent|Great|Wonderful|Perfect|Absolutely)[,\s]*',
    
    # Tail wagging and other dog-like actions
    r'\*?(?:wags?\s+tail|perks?\s+up|tilts?\s+head|ears?\s+perk)\*?\s*',
    
    # Emotional descriptors before speech
    r'^(?:warmly|thoughtfully|enthusiastically|gently|softly|knowingly|understandingly|approvingly|encouragingly|helpfully)\s*[,:]?\s*',
    
    # 🔧 NEW: Physical actions + speaking (clears throat and speaks in a friendly tone, etc.)
    r'^[^.!?]*\b(?:clears?|clears?\s+throat|adjusts?|adjusts?\s+glasses|leans?|leans?\s+forward|leans?\s+back|takes?\s+a\s+(?:deep\s+)?breath|pauses?|hesitates?)\s+(?:and\s+)?(?:speaks?|says?|replies?|responds?|talks?)\s+in\s+a\s+(?:\w+\s+)?(?:\w+\s+)?tone\s*[,:]?\s*',
    r'\b(?:clears?|clears?\s+throat|adjusts?|adjusts?\s+glasses|leans?|leans?\s+forward|leans?\s+back)\s+(?:and\s+)?(?:speaks?|says?)\s+in\s+a\s+\w+',
    
    # CRITICAL FIX: Remove XML-like result tags that shouldn't appear in responses
    r'<result>\s*',           # Remove opening <result> tags
    r'\s*</result>',          # Remove closing </result> tags
    r'</?result[^>]*>',       # Remove any variant of result tags
    
    # CRITICAL FIX: Remove internal processing artifacts that leak into responses
    # These patterns will be applied with DOTALL flag to handle multiline content
    r'<function_quality_reflection>[\s\S]*?</function_quality_reflection>\s*',  # Remove function quality reflection blocks (multiline)
    r'<function_quality_score>\s*\d+\s*</function_quality_score>\s*',           # Remove function quality scores
    r'</?function_quality_[^>]*>\s*',                                           # Remove any function quality opening/closing tags
    
    # Professional expertise disclaimers that should be filtered - comprehensive expert patterns
    
    # 🔧 NUCLEAR OPTION: Remove ANY "As a/an [words]..." at the very start (up to comma or period)
    r'^\s*["\']?As an? [^,:.!?]{1,100}[,:]?\s*',  # Catches "As an experienced dog care specialist," etc.
    
    # Dog/canine specific expert patterns
    r'^\s*["\']?As an? (?:expert|experienced|professional|certified|qualified) (?:dog|canine) (?:trainer|expert|specialist|behaviorist)["\']?\s*[,:]?\s*',
    r'\bAs an? (?:expert|experienced|professional|certified|qualified) (?:dog|canine) (?:trainer|expert|specialist|behaviorist)\b\s*[,:]?\s*',
    r'^\s*["\']?As an? (?:dog|canine) (?:training |behavior )?expert["\']?\s*[,:]?\s*',
    
    # Quoted expert patterns (handle quotes and commas better)
    r'^["\']As an? (?:expert|experienced|professional) (?:dog|canine) (?:trainer|expert)["\'][,]?\s*',
    r'^["\']As an? (?:dog|canine) expert["\'][:]?\s*',
    
    # More flexible dog expert combinations (handles "experienced dog training expert")
    r'^\s*["\']?As an? (?:experienced|professional|certified|qualified) (?:dog|canine) (?:training|behavior) expert["\']?\s*[,:]?\s*',
    r'\bAs an? (?:experienced|professional|certified|qualified) (?:dog|canine) (?:training|behavior) expert\b\s*[,:]?\s*',
    
    # CRITICAL FIX: "I'm [Name], an expert..." patterns (catches "I'm Mr. White, an experienced dog training expert")
    r"I'm [A-Z][a-z]+\.?\s+[A-Z][a-z]+,?\s+an? (?:experienced|professional|certified|qualified) (?:dog|canine) (?:training|behavior) expert\s*[,.]?\s*",
    r"I'm [A-Z][a-z]+\.?\s+[A-Z][a-z]+,?\s+an? (?:expert|experienced|professional|certified|qualified) (?:dog|canine) (?:trainer|expert|specialist|behaviorist)\s*[,.]?\s*",
    r"Hello!?\s+I'm [A-Z][a-z]+\.?\s+[A-Z][a-z]+,?\s+an? (?:experienced|professional|certified|qualified) (?:dog|canine) (?:training|behavior) expert\s*[,.]?\s*",
    
    # More general "I'm an expert..." patterns
    r"I'm an? (?:experienced|professional|certified|qualified) (?:dog|canine) (?:training|behavior) expert\s*[,.]?\s*",
    r"I'm an? (?:expert|experienced|professional|certified|qualified) (?:dog|canine) (?:trainer|expert|specialist|behaviorist)\s*[,.]?\s*",
    
    # COMPREHENSIVE: Catch sentences that establish roleplay identity (removes full sentence)
    r"[^.!?]*I'm [A-Z][a-z]+\.?\s+[A-Z][a-z]+,?\s+an? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:training|behavior|care)? (?:expert|trainer|specialist|behaviorist)[^.!?]*[.!?]\s*",
    r"[^.!?]*I'm an? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:training|behavior|care)? (?:expert|trainer|specialist|behaviorist)[^.!?]*[.!?]\s*",
    
    # CRITICAL: Catch standalone expert descriptions without "I'm" (like "an experienced dog trainer and behaviorist")
    # FIXED: More comprehensive patterns that catch the complete phrase
    r"\ban? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:trainer|expert|specialist|behaviorist)(?:\s+and\s+(?:trainer|expert|specialist|behaviorist))?\.?\s*",
    r"\ban? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:training|behavior|care) (?:expert|specialist)(?:\s+and\s+(?:trainer|expert|specialist|behaviorist))?\.?\s*",
    
    # Catch variations like "dog trainer and behaviorist" or "training expert and specialist"  
    r"\b(?:dog|canine|pet|animal) (?:trainer|expert|specialist|behaviorist)\s+and\s+(?:trainer|expert|specialist|behaviorist)\.?\s*",
    r"\b(?:training|behavior|care) (?:expert|specialist)\s+and\s+(?:trainer|expert|specialist|behaviorist)\.?\s*",
    
    # COMPREHENSIVE: Catch ANY combination of trainer/expert/behaviorist/specialist with "and"
    r"\b(?:trainer|expert|specialist|behaviorist)\s+and\s+(?:trainer|expert|specialist|behaviorist)\.?\s*",
    
    # Catch "Hello! I'm..." constructions specifically
    r"Hello!?\s+I'm [^.!?]*(?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:training|behavior|care)? (?:expert|trainer|specialist|behaviorist)[^.!?]*[.!?]\s*",
    
    # COMPREHENSIVE: "As an expert..." patterns - catch ALL variations
    # These catch any "As an expert in..." regardless of what follows
    r'^\s*["\']?As an? expert in [^,:.!?]*[,:]?\s*',                    # Start of line: "As an expert in [anything],"
    r'\bAs an? expert in [^,:.!?]*[,:]?\s*',                           # Anywhere: "As an expert in [anything],"
    r'^\s*["\']?As an? expert (?:in the |with )[^,:.!?]*[,:]?\s*',     # "As an expert in the [anything]," or "As an expert with [anything],"
    r'\bAs an? expert (?:in the |with )[^,:.!?]*[,:]?\s*',            # Same but anywhere in text
    
    # Specific patterns for common missed cases  
    r'^\s*["\']?As an? expert in (?:animal|dog|canine|pet) (?:companionship|training|behavior|care|health|psychology|welfare)["\']?\s*[,:]?\s*',
    r'\bAs an? expert in (?:animal|dog|canine|pet) (?:companionship|training|behavior|care|health|psychology|welfare)\b\s*[,:]?\s*',
    r'^\s*["\']?As an? expert in (?:dog|canine) training and behavior["\']?\s*[,:]?\s*',
    r'^\s*["\']?As an? expert in (?:dog|canine) (?:care and training|behavior and training)["\']?\s*[,:]?\s*',
    
    # CRITICAL: Remove full sentences that start with "As an expert..."
    r'As an? expert in [^.!?]*[.!?]\s*',                              # Remove entire sentence: "As an expert in [anything]."
    
    # CRITICAL: Catch expert statements that appear mid-sentence or after periods
    r'\.\s*As an? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:training|behavior|care)?\s*(?:and\s+)?(?:expert|trainer|specialist|behaviorist)[^.!?]*[.!?]?\s*',
    r'\.\s*I\'m an? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:training|behavior|care)?\s*(?:and\s+)?(?:expert|trainer|specialist|behaviorist)[^.!?]*[.!?]?\s*',
    
    # Remove complete sentences that contain expert identity anywhere
    r'[^.!?]*\ban? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:trainer|expert|specialist|behaviorist)\s+and\s+(?:trainer|expert|specialist|behaviorist)[^.!?]*[.!?]\s*',
    
    # General professional expertise patterns (document analyst, etc.)
    r'^\s*["\']?As an? expert (?:document|data|content|text|information) (?:analyst|specialist|expert)["\']?\s*[,:]?\s*',
    r'\bAs an? expert (?:document|data|content|text|information) (?:analyst|specialist|expert)\b\s*[,:]?\s*',
    
    # CRITICAL FIX: "As a [profession] specialist" patterns (the missing pattern!)
    r'^\s*["\']?As a (?:document|data|content|text|information|behavioral?|training|canine|dog|pet|animal) (?:analysis\s+)?(?:specialist|analyst|expert)["\']?\s*[,:]?\s*',
    r'\bAs a (?:document|data|content|text|information|behavioral?|training|canine|dog|pet|animal) (?:analysis\s+)?(?:specialist|analyst|expert)\b\s*[,:]?\s*',
    
    # Comprehensive "As a specialist" patterns  
    r'^\s*["\']?As a (?:\w+\s+)?specialist["\']?\s*[,:]?\s*',              # "As a [anything] specialist,"
    r'\bAs a (?:\w+\s+)?specialist\b\s*[,:]?\s*',                          # "As a specialist" anywhere
]

def clean_roleplay_response(response: str) -> str:
    """
    Remove roleplay actions and descriptive language from AI response
    
    Args:
        response: The AI response text
        
    Returns:
        Cleaned response without roleplay actions
    """
    if not response or not isinstance(response, str):
        return response
    
    original_response = response
    cleaned = response.strip()
    
    # IMPROVED: Handle bold text replacement specially, then apply other patterns
    # First, replace **bold text** with just the text content
    cleaned = re.sub(r'\*\*([^*]+?)\*\*', r'\1', cleaned, flags=re.IGNORECASE)
    
    # Apply all other roleplay removal patterns (skip the bold text pattern we handled above)
    bold_pattern = r'\*\*([^*]+?)\*\*'
    patterns_matched = []
    
    for i, pattern in enumerate(ROLEPLAY_PATTERNS):
        # Skip the bold text pattern since we handled it specially above
        if pattern == bold_pattern:
            continue
            
        # Check if pattern matches before applying it
        if re.search(pattern, cleaned, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL):
            patterns_matched.append(f"Pattern {i}: {pattern[:50]}...")
            
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    # Debug logging for pattern matches
    if patterns_matched:
        logger.debug(f"🔍 FILTER DEBUG: Patterns matched: {patterns_matched}")
    elif "expert" in original_response.lower():
        logger.warning(f"⚠️ FILTER DEBUG: 'expert' found in response but no patterns matched!")
        logger.warning(f"⚠️ FILTER DEBUG: Response snippet: {original_response[:100]}...")
    
    # Remove multiple spaces and clean up
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # Check if we removed processing artifacts (which is always OK)
    artifacts_removed = (
        "<function_quality_reflection>" in original_response or
        "<function_quality_score>" in original_response
    )
    
    # If we removed too much (over 30% of content), return original 
    # UNLESS we were removing processing artifacts (which is always allowed)
    if len(cleaned) < len(original_response) * 0.7 and not artifacts_removed:
        logger.warning(f"🚨 Response filter removed too much content, returning original")
        return original_response
    elif artifacts_removed:
        logger.info(f"✅ FILTER DEBUG: Successfully removed internal processing artifacts")
    
    # Log if we made changes
    if cleaned != original_response:
        logger.info(f"🧹 Filtered roleplay actions from response")
        logger.debug(f"Original: {original_response[:100]}...")
        logger.debug(f"Cleaned: {cleaned[:100]}...")
    
    return cleaned

def ensure_response_completeness(response: str) -> str:
    """
    Check if response appears to be truncated and attempt to clean it up
    
    Args:
        response: The AI response text
        
    Returns:
        Response cleaned of truncation indicators
    """
    if not response or not isinstance(response, str):
        return response
    
    response = response.strip()
    
    truncation_patterns = [
        r'\.\.\.$',           # Ends with ...
        r'\s+\.\.\.$',        # Ends with spaces then ...
        r'[^.!?]\s*$',        # Doesn't end with proper punctuation
        r'\w+\s*$'            # Ends mid-word without punctuation
    ]
    
    # Remove trailing ellipsis if found
    if re.search(r'\.\.\.$', response):
        response = re.sub(r'\.\.\.$', '.', response)
        logger.info("🔧 Removed truncation ellipsis")
    
    # If response doesn't end with proper punctuation, add period
    if response and not re.search(r'[.!?]$', response):
        # Only add period if it doesn't end with a colon (for lists) or other special cases
        if not re.search(r'[:;\-]$', response):
            response += '.'
            logger.info("🔧 Added proper sentence ending")
    
    return response

def is_response_professional(response: str) -> bool:
    """
    Check if response contains professional language vs roleplay
    
    Args:
        response: The AI response text
        
    Returns:
        True if professional, False if contains roleplay
    """
    if not response or not isinstance(response, str):
        return True
    
    # Check for obvious roleplay indicators
    roleplay_indicators = [
        r'chuckles?\s+warmly',
        r'smiles?\s+warmly', 
        r'nods?\s+thoughtfully',
        r'\*[^*]+\*',
        r'wags?\s+tail',
        r'perks?\s+up',
        r'^warmly[,:]',
        r'^thoughtfully[,:]',
        r'^enthusiastically[,:]',
        
        # 🔧 CRITICAL: XML/HTML result tags that shouldn't appear in user-facing responses
        r'<result>',
        r'</result>',
        r'</?result[^>]*>',
        
        # 🔧 MOST AGGRESSIVE: Catch ANY "As a/an [anything]" at the start
        r'^As an? \w+',  # Catches "As a specialist", "As an experienced", "As a dog trainer", etc.
        
        # CRITICAL: Expert identity patterns (triggers filtering for "I'm [name], an experienced dog training expert")
        r"I'm [A-Z][a-z]+\.?\s+[A-Z][a-z]+,?\s+an? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:training|behavior|care)?\s*(?:expert|trainer|specialist|behaviorist)",
        r"I'm an? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:training|behavior|care)?\s*(?:expert|trainer|specialist|behaviorist)",
        r"As an? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:training|behavior|care)?\s*(?:expert|trainer|specialist|behaviorist)",
        r"Hello!?\s+I'm.*(?:experienced|professional|certified|qualified).*(?:dog|canine|pet|animal).*(?:expert|trainer|specialist|behaviorist)",
        
        # COMPREHENSIVE: Catch ANY "As an expert..." statement
        r"As an? expert in ",                                            # Any "As an expert in [anything]"
        r"As an? expert (?:in the |with )",                              # "As an expert in the [anything]" or "As an expert with [anything]"
        
        # CRITICAL FIX: Catch "As a [profession] specialist" statements (the missing detection!)
        r"As a (?:document|data|content|text|information|behavioral?|training|canine|dog|pet|animal) (?:analysis\s+)?(?:specialist|analyst|expert)",
        r"As a (?:\w+\s+)?specialist",                                   # "As a [anything] specialist"
        
        # CRITICAL: Catch standalone expert descriptions (the current issue!)
        r"\ban? (?:experienced|professional|certified|qualified) (?:dog|canine|pet|animal) (?:trainer|expert|specialist|behaviorist)(?:\s+and\s+(?:trainer|expert|specialist|behaviorist))?",
        r"\b(?:dog|canine|pet|animal) (?:trainer|expert|specialist|behaviorist)\s+and\s+(?:trainer|expert|specialist|behaviorist)",
        r"\b(?:training|behavior|care) (?:expert|specialist)\s+and\s+(?:trainer|expert|specialist|behaviorist)",
        r"\b(?:trainer|expert|specialist|behaviorist)\s+and\s+(?:trainer|expert|specialist|behaviorist)",  # Catch any "X and Y" combinations
    ]
    
    for pattern in roleplay_indicators:
        if re.search(pattern, response, re.IGNORECASE):
            return False
    
    return True

def ensure_professional_start(response: str) -> str:
    """
    Ensure response starts professionally, not with roleplay
    
    Args:
        response: The AI response text
        
    Returns:
        Response with professional start
    """
    if not response or not isinstance(response, str):
        return response
    
    # Common unprofessional starters to replace
    unprofessional_starters = [
        (r'^chuckles?\s+warmly[,\s]*', ''),
        (r'^smiles?\s+warmly[,\s]*', ''),
        (r'^nods?\s+thoughtfully[,\s]*', ''),
        (r'^\*[^*]+\*\s*', ''),
        (r'^warmly[,:\s]+', ''),
        (r'^thoughtfully[,:\s]+', ''),
        (r'^enthusiastically[,:\s]+', ''),
    ]
    
    cleaned = response
    for pattern, replacement in unprofessional_starters:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    
    # Ensure first word is capitalized after cleaning
    cleaned = cleaned.strip()
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    
    return cleaned

def filter_ai_response(response: str) -> str:
    """
    Complete response filtering pipeline
    
    Args:
        response: Raw AI response
        
    Returns:
        Professionally filtered response
    """
    if not response:
        return response
    
    # DEBUG: Log if we see expert patterns or double asterisks
    if "As an experienced dog expert" in response:
        logger.info("🐛 FILTER DEBUG: Found 'As an experienced dog expert' in response")
    if "**" in response:
        logger.info("🐛 FILTER DEBUG: Found double asterisks (**) in response")
        logger.info(f"🐛 FILTER DEBUG: Response snippet: '{response[:100]}...'")
    
    # Step 1: Remove roleplay actions
    filtered = clean_roleplay_response(response)
    
    # Step 2: Ensure professional start
    filtered = ensure_professional_start(filtered)
    
    # Step 3: Ensure response completeness (fix truncation)
    filtered = ensure_response_completeness(filtered)
    
    # Step 4: Final cleanup
    filtered = filtered.strip()
    
    # DEBUG: Log if filtering worked
    if "As an experienced dog expert" in response and "As an experienced dog expert" not in filtered:
        logger.info("✅ FILTER DEBUG: Successfully removed 'As an experienced dog expert'")
    elif "As an experienced dog expert" in filtered:
        logger.warning("❌ FILTER DEBUG: Failed to remove 'As an experienced dog expert'")
        
    if "**" in response and "**" not in filtered:
        logger.info("✅ FILTER DEBUG: Successfully removed double asterisks (**)")
    elif "**" in filtered:
        logger.warning("❌ FILTER DEBUG: Failed to remove double asterisks (**)") 
        logger.warning(f"❌ FILTER DEBUG: Remaining in filtered: '{filtered[:100]}...'") 
    
    return filtered
