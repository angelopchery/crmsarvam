"""
Intelligence extraction service for extracting follow-ups and deadlines from transcripts.
"""
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFollowUp:
    """Data class for extracted follow-up."""

    description: str
    date: Optional[datetime] = None


@dataclass
class ExtractedDeadline:
    """Data class for extracted deadline."""

    description: str
    due_date: datetime


class IntelligenceExtractor:
    """Service for extracting intelligence (follow-ups, deadlines) from transcripts."""

    # Common follow-up keywords
    FOLLOW_UP_KEYWORDS = [
        "follow up",
        "follow-up",
        "check back",
        "get back to",
        "reach out",
        "contact",
        "discuss",
        "schedule",
        "set up",
        "arrange",
        "plan",
        "review",
        "meeting",
        "call",
        "followup",
        "followup with",
    ]

    # Common deadline/due date keywords
    DEADLINE_KEYWORDS = [
        "deadline",
        "due date",
        "submit by",
        "complete by",
        "finish by",
        "target date",
        "delivery date",
        "expected by",
        "needed by",
        "required by",
        "before",
        "by the end of",
        "no later than",
    ]

    # Date/time patterns
    DATE_PATTERNS = [
        # Specific dates: Jan 15, January 15th, 15th Jan, etc.
        r"(?:by|on|before|after)?\s*(?:the\s+)?(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)",
        r"(?:by|on|before|after)?\s*(?:the\s+)?((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?)",

        # Tomorrow, next week, next month
        r"(?:by|on|before|after)?\s+(tomorrow|today|next\s+(?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday))",

        # In X days/weeks/months
        r"in\s+(\d+)\s+(day|days|week|weeks|month|months)",

        # End of week/month
        r"(?:by|on|before)?\s+(?:the\s+)?end\s+of\s+(this\s+)?(week|month|quarter|year)",

        # Numeric dates: 15-01-2024, 15/01/2024
        r"(?:by|on|before|after)?\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})",
    ]

    def __init__(self):
        """Initialize IntelligenceExtractor."""
        # Compile regex patterns for better performance
        self.date_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in self.DATE_PATTERNS]

    def extract_from_transcript(
        self, transcript: str
    ) -> Tuple[List[ExtractedFollowUp], List[ExtractedDeadline]]:
        """
        Extract follow-ups and deadlines from transcript text.

        Args:
            transcript: The transcribed text

        Returns:
            Tuple of (follow_ups, deadlines) lists
        """
        logger.info("Extracting intelligence from transcript")
        logger.debug(f"Transcript length: {len(transcript)} chars")

        follow_ups = self._extract_follow_ups(transcript)
        deadlines = self._extract_deadlines(transcript)

        logger.info(f"Extracted {len(follow_ups)} follow-ups and {len(deadlines)} deadlines")

        return follow_ups, deadlines

    def _extract_follow_ups(self, transcript: str) -> List[ExtractedFollowUp]:
        """
        Extract follow-up actions from transcript.

        Args:
            transcript: The transcribed text

        Returns:
            List of extracted follow-ups
        """
        follow_ups = []
        sentences = self._split_into_sentences(transcript)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if sentence contains follow-up keywords
            if self._contains_keywords(sentence, self.FOLLOW_UP_KEYWORDS):
                # Extract the action/task description
                description = self._clean_description(sentence)
                if description:
                    # Try to extract a date
                    date = self._extract_date(sentence)
                    follow_ups.append(ExtractedFollowUp(description=description, date=date))
                    logger.debug(f"Extracted follow-up: {description}")

        # Deduplicate similar follow-ups
        return self._deduplicate_follow_ups(follow_ups)

    def _extract_deadlines(self, transcript: str) -> List[ExtractedDeadline]:
        """
        Extract deadlines from transcript.

        Args:
            transcript: The transcribed text

        Returns:
            List of extracted deadlines
        """
        deadlines = []
        sentences = self._split_into_sentences(transcript)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if sentence contains deadline keywords
            if self._contains_keywords(sentence, self.DEADLINE_KEYWORDS):
                # Extract the description
                description = self._clean_description(sentence)
                if description:
                    # Try to extract a due date (required for deadlines)
                    due_date = self._extract_date(sentence)
                    if due_date:
                        deadlines.append(ExtractedDeadline(description=description, due_date=due_date))
                        logger.debug(f"Extracted deadline: {description} by {due_date}")

        # Deduplicate similar deadlines
        return self._deduplicate_deadlines(deadlines)

    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.

        Args:
            text: Input text

        Returns:
            List of sentences
        """
        # Simple sentence splitting - can be enhanced with NLP
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _contains_keywords(self, text: str, keywords: List[str]) -> bool:
        """
        Check if text contains any of the keywords.

        Args:
            text: Text to check
            keywords: List of keywords to search for

        Returns:
            True if any keyword is found
        """
        text_lower = text.lower()
        return any(keyword.lower() in text_lower for keyword in keywords)

    def _clean_description(self, text: str) -> str:
        """
        Clean and normalize description text.

        Args:
            text: Raw description text

        Returns:
            Cleaned description
        """
        # Remove filler words and normalize
        text = re.sub(r'\b(um|uh|like|you know)\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()

        # Capitalize first letter
        if text:
            text = text[0].upper() + text[1:]

        # Ensure it ends with punctuation
        if text and not text[-1] in '.!?':
            text += '.'

        return text

    def _extract_date(self, text: str) -> Optional[datetime]:
        """
        Extract and parse a date from text.

        Args:
            text: Text containing date

        Returns:
            Parsed datetime or None if not found/parseable
        """
        now = datetime.utcnow()

        # Check for relative dates first
        text_lower = text.lower()

        if "today" in text_lower:
            return now.replace(hour=17, minute=0, second=0, microsecond=0)  # 5 PM today
        elif "tomorrow" in text_lower:
            return (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
        elif "next week" in text_lower:
            return (now + timedelta(weeks=1)).replace(hour=17, minute=0, second=0, microsecond=0)
        elif "next month" in text_lower:
            next_month = now.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)
            return next_month.replace(hour=17, minute=0, second=0, microsecond=0)

        # Check for "end of week/month"
        if "end of week" in text_lower:
            days_until_friday = (4 - now.weekday()) % 7
            return (now + timedelta(days=days_until_friday)).replace(hour=17, minute=0, second=0, microsecond=0)
        elif "end of month" in text_lower:
            next_month = now.replace(day=28) + timedelta(days=4)
            return next_month.replace(day=1, hour=17, minute=0, second=0, microsecond=0) - timedelta(days=1)

        # Check for "in X days/weeks"
        match = re.search(r'in\s+(\d+)\s+(day|days|week|weeks|month|months)', text_lower)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)

            if "day" in unit:
                return now + timedelta(days=amount)
            elif "week" in unit:
                return now + timedelta(weeks=amount)
            elif "month" in unit:
                # Approximate month as 30 days
                return now + timedelta(days=amount * 30)

        # Try regex patterns for specific dates
        for date_regex in self.date_regexes:
            match = date_regex.search(text)
            if match:
                try:
                    date_str = match.group(1) or match.group(0)
                    # Try to parse with dateutil if available, otherwise simple parsing
                    try:
                        from dateutil import parser
                        parsed_date = parser.parse(date_str, fuzzy=True)
                        return parsed_date
                    except ImportError:
                        # Fallback simple parsing
                        return self._parse_simple_date(date_str, now)
                except Exception:
                    continue

        return None

    def _parse_simple_date(self, date_str: str, reference: datetime) -> Optional[datetime]:
        """
        Simple date parser fallback.

        Args:
            date_str: Date string to parse
            reference: Reference datetime for relative calculations

        Returns:
            Parsed datetime or None
        """
        # This is a simplified fallback - in production, use dateutil
        # Handle numeric dates like 15-01-2024
        if re.match(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}', date_str):
            try:
                parts = re.split(r'[-/]', date_str)
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2]) if len(parts[2]) == 4 else 2000 + int(parts[2])
                return datetime(year, month, day, 17, 0, 0)
            except (ValueError, IndexError):
                pass

        return None

    def _deduplicate_follow_ups(self, follow_ups: List[ExtractedFollowUp]) -> List[ExtractedFollowUp]:
        """
        Remove duplicate follow-ups based on description similarity.

        Args:
            follow_ups: List of follow-ups to deduplicate

        Returns:
            Deduplicated list
        """
        seen = set()
        unique = []

        for follow_up in follow_ups:
            # Simple deduplication - exact match
            key = follow_up.description.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(follow_up)

        return unique

    def _deduplicate_deadlines(self, deadlines: List[ExtractedDeadline]) -> List[ExtractedDeadline]:
        """
        Remove duplicate deadlines based on description similarity.

        Args:
            deadlines: List of deadlines to deduplicate

        Returns:
            Deduplicated list
        """
        seen = set()
        unique = []

        for deadline in deadlines:
            # Simple deduplication - exact match
            key = deadline.description.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(deadline)

        return unique
