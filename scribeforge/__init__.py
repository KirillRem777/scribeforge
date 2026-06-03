"""scribeforge — turn talks and videos into clean, readable transcripts.

Pipeline: fetch audio -> transcribe (whisper.cpp) -> repair loops ->
polish (LLM) -> render PDF/Markdown.
"""

__version__ = "0.1.0"
