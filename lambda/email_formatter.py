"""
Email formatting utilities for creating beautiful HTML and plain text emails.

Provides templates and formatting functions for daily stoic reflection emails.
"""

import html
from typing import Dict


def format_html_email(
    quote: str,
    attribution: str,
    reflection: str,
    theme: str,
    journaling_prompt: str = "",
    magic_link: str = ""
) -> str:
    """
    Format the daily reflection as an HTML email.

    Args:
        quote: The stoic quote text
        attribution: Quote attribution (e.g., "Marcus Aurelius - Meditations 4.3")
        reflection: The reflection text (250-450 words)
        theme: Monthly theme name
        journaling_prompt: Journaling prompt (optional, Phase 3)
        magic_link: Magic link URL for web app access (optional, Phase 3)

    Returns:
        Complete HTML email as a string
    """
    # Escape HTML special characters
    quote_safe = html.escape(quote)
    attribution_safe = html.escape(attribution)
    theme_safe = html.escape(theme)
    journaling_prompt_safe = html.escape(journaling_prompt) if journaling_prompt else ""

    # Format reflection with paragraphs
    reflection_html = format_reflection_paragraphs(reflection)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Daily Stoic Reflection</title>
    <style>
        body {{
            font-family: Georgia, 'Times New Roman', serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #2c3e50;
            padding-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            color: #2c3e50;
            font-size: 28px;
        }}
        .theme {{
            color: #7f8c8d;
            font-style: italic;
            font-size: 14px;
            margin-top: 5px;
        }}
        .quote {{
            font-size: 18px;
            font-style: italic;
            color: #34495e;
            margin: 30px 0;
            padding: 20px;
            background-color: #ecf0f1;
            border-left: 4px solid #3498db;
        }}
        .attribution {{
            text-align: right;
            color: #7f8c8d;
            font-size: 14px;
            margin-top: 10px;
        }}
        .reflection {{
            margin-top: 30px;
            font-size: 16px;
            text-align: justify;
        }}
        .reflection p {{
            margin-bottom: 15px;
        }}
        .journaling-prompt {{
            margin-top: 30px;
            padding: 20px;
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            border-radius: 4px;
        }}
        .journaling-prompt h3 {{
            margin: 0 0 10px 0;
            color: #856404;
            font-size: 16px;
        }}
        .journaling-prompt p {{
            margin: 0;
            color: #856404;
            font-size: 14px;
        }}
        .cta-button {{
            margin-top: 30px;
            text-align: center;
        }}
        .cta-button a {{
            display: inline-block;
            padding: 15px 30px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: bold;
        }}
        .cta-button a:hover {{
            background-color: #2980b9;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            font-size: 12px;
            color: #95a5a6;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Morning Reflection</h1>
            <div class="theme">{theme_safe}</div>
        </div>

        <div class="quote">
            {quote_safe}
            <div class="attribution">— {attribution_safe}</div>
        </div>

        <div class="reflection">
            {reflection_html}
        </div>

        {f'''
        <div class="journaling-prompt">
            <h3>📝 Today's Journaling Prompt</h3>
            <p>{journaling_prompt_safe}</p>
        </div>
        ''' if journaling_prompt else ''}

        {f'''
        <div class="cta-button">
            <a href="{magic_link}">Read & Journal Online</a>
        </div>
        ''' if magic_link else ''}

        <div class="footer">
            Morning Reflection • Powered by Claude
        </div>
    </div>
</body>
</html>"""

    return html_template


def format_plain_text_email(
    quote: str,
    attribution: str,
    reflection: str,
    journaling_prompt: str = ""
) -> str:
    """
    Format the daily reflection as plain text email (fallback).

    Args:
        quote: The stoic quote text
        attribution: Quote attribution
        reflection: The reflection text
        journaling_prompt: Journaling prompt (optional, Phase 3)

    Returns:
        Plain text email as a string
    """
    divider = "=" * 70

    plain_text = f"""
{divider}
MORNING REFLECTION
{divider}

"{quote}"

— {attribution}

{divider}

{reflection}

{f'''
{divider}
📝 Today's Journaling Prompt
{divider}

{journaling_prompt}

''' if journaling_prompt else ''}
{divider}
Morning Reflection • Powered by Claude
"""

    return plain_text.strip()


def format_reflection_paragraphs(reflection: str) -> str:
    """
    Format reflection text into HTML paragraphs.

    Args:
        reflection: Raw reflection text

    Returns:
        HTML formatted reflection with <p> tags
    """
    # Split on double newlines to detect paragraphs
    paragraphs = reflection.split('\n\n')

    # Escape HTML and wrap in <p> tags
    formatted_paragraphs = []
    for para in paragraphs:
        # Remove extra whitespace and newlines within paragraph
        cleaned = ' '.join(para.split())
        if cleaned:  # Only add non-empty paragraphs
            escaped = html.escape(cleaned)
            formatted_paragraphs.append(f"<p>{escaped}</p>")

    return '\n            '.join(formatted_paragraphs)


def create_email_subject(theme: str) -> str:
    """
    Create the email subject line.

    Args:
        theme: Monthly theme name

    Returns:
        Email subject line
    """
    return f"Daily Stoic Reflection: {theme}"


def validate_email_content(quote: str, attribution: str, reflection: str) -> Dict[str, bool]:
    """
    Validate email content meets basic requirements.

    Args:
        quote: The stoic quote text
        attribution: Quote attribution
        reflection: The reflection text

    Returns:
        Dictionary with validation results
    """
    validation = {
        "has_quote": bool(quote and len(quote.strip()) > 0),
        "has_attribution": bool(attribution and len(attribution.strip()) > 0),
        "has_reflection": bool(reflection and len(reflection.strip()) > 0),
        "reflection_min_length": len(reflection.split()) >= 200,  # Roughly 200 words minimum
        "reflection_max_length": len(reflection.split()) <= 500,  # Roughly 500 words maximum
    }

    validation["is_valid"] = all([
        validation["has_quote"],
        validation["has_attribution"],
        validation["has_reflection"],
        validation["reflection_min_length"]
    ])

    return validation
