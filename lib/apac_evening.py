"""The APAC Evening Update — script generator.

A daily evening audio show covering the day's major regulatory
developments across APAC in five beats: Fraud, Financial Crime,
Prudential Risk, Infrastructure and Digital Assets.

Why evening: Regulation Asia and the regulator sites publish through the
Asian business day, so an evening run sees a complete day rather than
yesterday's leftovers.

Five presenters, because a beat show needs someone who owns each beat —
a single anchor reading five subjects flattens into a bulletin, which is
the thing this is not. The crime desk deliberately carries both Fraud
and Financial Crime: they are adjacent disciplines, and Fraud alone is
too thin on most days to justify its own voice.

Distribution note: this publishes to TrustSphere first as a pilot. The
script therefore credits and drives to the Regulation Asia platform
throughout — that is the point of the exercise, not a courtesy.
"""

from __future__ import annotations

import datetime as dt
import os
import re
from dataclasses import dataclass, field

from lib.ra_beats import (
    BEATS,
    DIGITAL_ASSETS,
    FINANCIAL_CRIME,
    FRAUD,
    INFRASTRUCTURE,
    PRUDENTIAL_RISK,
    UNMATCHED,
    bucket,
    is_apac,
)

CLAUDE_MODEL = "claude-sonnet-5"

# Markets the show is expected to keep an eye on. Used to tell the
# script which majors had nothing today, so the anchor can say so
# instead of leaving a silent gap that reads as missed coverage.
MAJOR_MARKETS = [
    "Singapore", "Hong Kong", "Malaysia", "Australia", "India",
    "Japan", "Korea", "China", "Indonesia", "Philippines", "Thailand",
]


@dataclass
class Presenter:
    tag: str            # speaker marker used in the script and by the renderer
    name: str
    beats: list[str]
    brief: str          # who they are, in the prompt's voice


# Two hosts, as the briefing has always run. They carry all five beats
# between them — Jordan owns the crime desk, Alex takes prudential and
# markets, and digital assets goes to whoever has the better argument.
# A five-presenter rota was tried and dropped: it turned handovers into
# most of the runtime and made the disagreements shallower, because two
# people who know each other's positions argue better than five people
# being introduced.
PRESENTERS: list[Presenter] = [
    Presenter(
        tag="ALEX",
        name="Alex",
        beats=[PRUDENTIAL_RISK, INFRASTRUCTURE],
        brief=(
            "Lead host. British, ex-regulator, twenty years of it. Sets "
            "the frame, moves the show between beats, and takes the "
            "prudential and market-structure stories himself. Dry, "
            "understates everything — which is how you can tell when he "
            "thinks something matters. Reads a consultation paper and "
            "sees the balance-sheet consequence three years out. "
            "Interrupts the moment an answer goes abstract: 'sorry, who "
            "actually pays for that?' Will admit when he does not know "
            "something and ask."
        ),
    ),
    Presenter(
        tag="JORDAN",
        name="Jordan",
        beats=[FRAUD, FINANCIAL_CRIME, DIGITAL_ASSETS],
        brief=(
            "Co-host and practitioner. British, front-line MLRO — has "
            "filed the STRs, sat through the inspection, been the one "
            "explaining to the board why the backlog exists. Warm, fast, "
            "completely out of patience with policy that sounds decisive "
            "and changes nothing on Monday morning. Reaches for the "
            "specific case over the general principle. Watches the digital "
            "asset stories for where the licensing perimeter falls, and "
            "refuses to call a pilot adoption. Will say 'I have done this "
            "job, and that is not how it works.'"
        ),
    ),
]


@dataclass
class Guest:
    """An occasional third voice.

    Guests appear when they have standing on a specific story, not on a
    schedule — a guest with nothing particular to add is worse than two
    hosts who know each other's rhythm. The guest takes one segment,
    brings experience the hosts do not have, and is argued with rather
    than deferred to.
    """
    tag: str
    name: str
    brief: str
    beat: str | None = None   # segment they join; None lets the script decide


# David presenting as himself, once his voice is cloned. Written as a
# practitioner rather than a vendor: he is on for what he has seen, and
# the moment it reads as a pitch the segment stops being worth airing.
DAVID_GUEST = Guest(
    tag="DAVID",
    name="David Haynes",
    beat=FRAUD,
    brief=(
        "Guest. Hong Kong-based fraud and financial crime specialist who "
        "sits with heads of compliance and MLROs across Asia most weeks. "
        "On because he has seen the pattern being discussed happen "
        "repeatedly, and can say what firms actually do about it rather "
        "than what the guidance says they should. Talks in cases and "
        "numbers he has seen, hedges when he is generalising from a small "
        "sample, and says so. Alex and Jordan push back on him exactly as "
        "hard as they push on each other — deference would make the "
        "segment worthless."
    ),
)

BEAT_ORDER = [FRAUD, FINANCIAL_CRIME, PRUDENTIAL_RISK, INFRASTRUCTURE, DIGITAL_ASSETS]

SYSTEM_PROMPT = """You write The APAC Evening Update, a daily audio show on \
Asia-Pacific financial regulation for compliance, risk and financial-crime \
professionals. Your listener is an MLRO, a head of compliance, or a risk \
officer at a bank, fintech or exchange somewhere between Mumbai and Auckland, \
listening on the way home.

THE STANDARD
The show is worth fifteen minutes of a senior person's evening or it is worth \
nothing. That means: every story must carry a consequence, not just an \
announcement. "The regulator published a consultation" is not a story. "The \
regulator published a consultation that moves the reporting threshold, and if \
you are a mid-sized MSB in Kuala Lumpur your Q1 build just changed" is a story.

Never pad. If a beat has one good story, cover one story well. A short \
segment is a professional judgement; a long segment made of filler is a waste \
of the listener's time and they will not come back.

THE HOSTS — they are not interchangeable
{presenter_briefs}

HOW THEY TALK — THE MOST IMPORTANT SECTION HERE
This must sound like two people talking, recorded. Not two people reading. \
Every instruction below exists because the alternative is the flat, tidy, \
evenly-portioned cadence that makes a listener think "this was generated", \
and once they think it they stop listening.

Turn length is the biggest tell. Real conversation is wildly uneven. Some \
turns run ninety words because someone is working through an argument. Some \
are four words. Some are one — "Exactly." "Mm." "When?" If your turns are \
all roughly the same size, you have written a script, not a conversation. \
Include at least four turns under six words.

They interrupt each other, genuinely. A turn can stop mid-sentence because \
the other one has cut in — end it on a dash and let them take over. The \
interrupted one sometimes finishes their point afterwards, sometimes does \
not bother.

They think while speaking. They start a sentence, stop, and restart it a \
different way. They correct themselves on a figure — "it was four hundred \
million, sorry, four-ten." They trail off when the thought runs out. They \
say "I do not know" when they do not know.

They react before they respond. "Hang on." "No, that is the bit I do not \
buy." "Right, but —". A reaction is its own turn; it does not need to be \
glued to the front of a longer one.

They refer back. To something said earlier in this episode, to a story from \
last week, to their own past jobs — "I sat in that meeting", "we said in \
June this would happen". This is what makes them people rather than \
narrators.

Disagreement is real and often unresolved. One of them is sometimes simply \
not persuaded, and the segment moves on with that hanging. Nobody \
summarises the disagreement for the listener's benefit.

BANNED, because these are the fingerprints of generated dialogue
- "That is a great point." "Absolutely." "Exactly right." "Well said." Any \
turn that opens by complimenting or validating the previous turn.
- Restating what the other person just said before replying to it.
- Signposting: "First... second... finally", "Three things here", "Let me \
break that down", "There are two issues".
- Grouping everything into threes. Real arguments have one point, or five.
- Both hosts speaking in the same register and rhythm. Alex understates \
and is dry. Jordan is faster, warmer, blunter. A reader should be able to \
tell who is talking with the tags removed.
- Ending every segment on a neat summarising line before the handover.
- Rhetorical questions asked only to answer them.
- Perfectly alternating ALEX, JORDAN, ALEX, JORDAN all the way down. This \
one is easy to miss because dialogue naturally alternates, so make it \
deliberate: at least three times in the episode, give the same speaker two \
consecutive tagged turns. They pause, then add the thing they were still \
chewing on. Write it as two separate turns with the same tag, not one long \
one — the gap between them is doing the work.

No hype vocabulary. No "shocking", "groundbreaking", "game-changing", \
"landmark". No throat-clearing openers like "Welcome back" more than once. \
Sentences of twelve to twenty-two words, except when someone is interrupted. \
Contractions throughout. Say numbers the way a person says them out loud — \
"about one-point-two billion", not "1.2bn".

EVERY WORD IS READ ALOUD BY A SPEECH ENGINE. Write what should be heard.
- Always write "Asia Pacific". Never write "APAC" — it is read as letters \
and sounds wrong.
- Spell out any acronym the first time unless it is genuinely said as a word \
in the industry. "The Monetary Authority of Singapore, MAS" on first use, \
then MAS after that.
- No symbols the engine cannot voice: write "per cent", "dollars", "and", \
not %, $, &. Write dates as spoken — "the fourteenth of January", not 14/01.
- No parentheses, bullet points, headings or markdown anywhere in the body.

Do not invent. Every fact must come from the source material below. If a date, \
figure or name is not in the source, do not state it. Where the source is \
thin, say the source is thin — "the notice does not say when" is an honest and \
useful sentence.

REGULATION ASIA
The reporting underpinning this show is Regulation Asia's. Credit them by name \
when a story comes from their reporting — naturally, in the flow of speech, \
not as a disclaimer. Two or three times across the episode, not every story. \
The anchor closes by pointing listeners to the Regulation Asia platform for \
the full reporting and the detail the show could not fit. Make that close \
specific to something in today's episode, not a generic plug.

FORMAT
Open with a title line, then a summary line, then the script.

TITLE: <6-10 words, specific to today, no colon-subtitle construction>
SUMMARY: <one sentence, under 30 words, for the episode notes>

Then the body. Every spoken turn begins with the speaker tag, exactly as \
written here: {speaker_tags}

ALEX: [spoken words]
JORDAN: [spoken words]

Nothing else — no stage directions, no [MUSIC], no segment headers, no \
markdown. The words are read aloud exactly as written.

LENGTH
{length_instruction}

STRUCTURE
1. Alex opens on the thread connecting today, not a list of headlines.
2. Then the stories — in beat order where more than one beat makes the cut: \
Fraud, Financial Crime, Prudential Risk, Infrastructure, Digital Assets. Do \
not announce beat names as segment headers. Move between subjects the way a \
conversation moves.
3. Close: the one thing to do before the end of the week, then the pointer \
to Regulation Asia.

SELECTION — this is the hardest part of the job
You are given every story of the day and you cannot use them all. Choose the \
three or four that carry the largest consequence for the listener, and give \
those room. A show that covers four stories properly beats one that mentions \
twelve.

Choosing means leaving good material out, including entire beats. A night \
with no digital assets segment is a normal night. Do not include a story \
merely to tick a beat, and never announce what you are skipping — an \
audience notices depth, not coverage.

Two or three of the remaining stories may get a single sentence each near the \
end, if they genuinely matter and the hosts would mention them. That is a \
passing reference between colleagues, not a headline round-up.
{guest_instruction}"""


# Effective spoken pace once Edge TTS renders at podcast.EDGE_RATE.
# Dropped from 165 when the rate went from +10% to -7% — the words in a
# minute fall with it, so a target of "8 minutes" written against the
# old figure would now run closer to nine and a half.
WORDS_PER_MINUTE = 140


def _length_instruction(target_minutes: int | None) -> str:
    """Length guidance. None means the material decides.

    A fixed target is the enemy of this show. Told to hit a number, the
    model pads a thin day and truncates a heavy one, and padding is the
    single most artificial thing a conversation can do."""
    if target_minutes is None:
        return (
            "There is no target length. The material decides. A day with "
            "two genuinely consequential developments is a short episode "
            "and should sound like one; a day with six is a long one. "
            "Roughly eight to twenty-five minutes is the normal range, at "
            f"about {WORDS_PER_MINUTE} words a minute, but treat that as "
            "observation rather than instruction.\n\n"
            "The only rule: every minute has to earn itself. Never restate "
            "a point because the episode feels short, never compress a "
            "genuinely important story because it feels long. If you catch "
            "yourself writing a sentence that exists to fill time, cut it "
            "and end the episode."
        )
    lo = int(target_minutes * (WORDS_PER_MINUTE - 10))
    hi = int(target_minutes * (WORDS_PER_MINUTE + 15))
    return (
        f"Aim for about {target_minutes} minutes, roughly {lo:,} to {hi:,} "
        "words across all speakers. Get there by covering the material "
        "properly, never by padding. If today's stories genuinely do not "
        "support it, write a shorter, better show."
    )


def _format_article(item, index: int) -> str:
    """One article as prompt source material."""
    topics = ", ".join((item.topics or [])[:4])
    body = (item.content or item.summary or "").strip()
    return (
        f"[{index}] {item.title}\n"
        f"    Published: {item.published} | Market: {item.jurisdiction or 'not market-specific'}\n"
        f"    Topics: {topics}\n"
        f"    Source: Regulation Asia — {item.url}\n"
        f"    {body}\n"
    )


def build_source_brief(
    items,
    *,
    today: dt.date,
    apac_only: bool = False,
) -> tuple[str, dict[str, list]]:
    """Assemble the prompt's source section, grouped by beat.

    Returns (brief_text, buckets) so the caller can report the same
    counts it fed the model."""
    buckets = bucket(items, apac_only=apac_only)

    parts: list[str] = [
        f"SOURCE MATERIAL — Regulation Asia, {today.strftime('%A %d %B %Y')}",
        f"{sum(len(v) for v in buckets.values())} articles, grouped by beat.",
        "",
    ]

    n = 0
    for beat in BEAT_ORDER:
        stories = buckets.get(beat, [])
        parts.append(f"===== {beat.upper()} — {len(stories)} article(s) =====")
        if not stories:
            parts.append("(nothing today — skip this segment entirely)\n")
            continue
        for item in stories:
            n += 1
            parts.append(_format_article(item, n))

    extra = buckets.get(UNMATCHED, [])
    if extra:
        parts.append(
            f"===== {UNMATCHED.upper()} — {len(extra)} article(s) =====\n"
            "Outside the five beats. Use only if one is too important to omit; "
            "otherwise ignore.\n"
        )
        for item in extra:
            n += 1
            parts.append(_format_article(item, n))

    covered = {
        i.jurisdiction for v in buckets.values() for i in v if i.jurisdiction
    }
    missing = [m for m in MAJOR_MARKETS if m not in covered]
    parts.append(
        "===== MARKET COVERAGE =====\n"
        f"Represented today: {', '.join(sorted(covered)) or 'none identified'}\n"
        f"No stories today from: {', '.join(missing) or 'none — all majors covered'}\n"
    )

    return "\n".join(parts), buckets


def system_prompt(*, target_minutes: int, guest: Guest | None = None) -> str:
    blocks = [
        f"{p.tag} — {p.name} (beats: {', '.join(p.beats)})\n    {p.brief}"
        for p in PRESENTERS
    ]
    tags = [p.tag for p in PRESENTERS]

    guest_instruction = ""
    if guest:
        where = (
            f"the {guest.beat} segment" if guest.beat
            else "whichever segment they have most standing on"
        )
        blocks.append(f"{guest.tag} — {guest.name} (guest)\n    {guest.brief}")
        tags.append(guest.tag)
        guest_instruction = (
            f"\n5. {guest.name} joins as a guest for {where}. Bring them in "
            "properly — Alex introduces who they are and why they are on "
            "this story, once, in a sentence. They are in that segment and "
            "largely out of the others, though they may chip in if something "
            "later touches their ground. They do not deliver the close."
        )

    return SYSTEM_PROMPT.format(
        presenter_briefs="\n\n".join(blocks),
        speaker_tags=", ".join(f"{t}:" for t in tags),
        length_instruction=_length_instruction(target_minutes),
        guest_instruction=guest_instruction,
    )


@dataclass
class EpisodeScript:
    title: str
    summary: str
    body: str
    buckets: dict[str, list] = field(default_factory=dict)
    usage: dict[str, int] = field(default_factory=dict)

    @property
    def word_count(self) -> int:
        return len(re.findall(r"\b[\w'-]+\b", self.body))

    @property
    def char_count(self) -> int:
        """Spoken characters only — what ElevenLabs actually bills for."""
        spoken = re.sub(r"^[A-Z]+:", "", self.body, flags=re.MULTILINE)
        return len(spoken)

    @property
    def estimated_minutes(self) -> float:
        return round(self.word_count / WORDS_PER_MINUTE, 1)

    def turns_by_speaker(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for line in self.body.splitlines():
            m = re.match(r"^([A-Z]+):", line.strip())
            if m:
                counts[m.group(1)] = counts.get(m.group(1), 0) + 1
        return counts


LINKEDIN_SYSTEM_PROMPT = """You write the daily LinkedIn post that goes out \
with The Asia Pacific Evening Update. It is published by the TrustSphere \
company page, not by an individual.

That sets the voice. A company page posting about regulation is presumed to \
be marketing until it proves otherwise, and compliance professionals scroll \
past marketing faster than anyone. The post earns attention by being useful \
on its own — someone who reads it and never clicks anything should still have \
learned something worth knowing. Institutional but not corporate: no "we are \
pleased to", no "our team", no first-person singular, and no talking about \
TrustSphere at all. The subject is the regulation, not the company.

The honesty bar is absolute. State nothing that is not in the source \
material. No invented figures, dates or names, no implied access to anything \
non-public. Where something is uncertain, say so. A company page that gets a \
regulatory fact wrong in front of this audience does not get a second look.

WHAT THE POST IS
One observation about today that a head of compliance in Singapore or Hong \
Kong would stop scrolling for. Not a summary of the episode. Not a headline \
list. Either one thing connecting two or three of today's developments, or a \
single story whose consequence is being under-read.

FORM
- Open with the observation itself. No greeting, no "Excited to share", no \
throat-clearing. The first line has to earn the second, because the rest is \
behind a "see more".
- Short paragraphs, one to two sentences each, blank line between. Read on a \
phone.
- 130 to 200 words. Shorter beats padded.
- Plain sentences. No emoji. Two hashtags at most, or none.
- British spelling. Contractions are fine — this should read as written by a \
person who knows the subject, not assembled by a brand.
- Name Regulation Asia as the source of the reporting, and point to the \
platform. Attribution inside a sentence, not a sign-off ad.
- Close by pointing to tonight's episode, in one short line.

Do not use the words "thrilled", "delighted", "proud", "game-changer", "deep \
dive", "unpack", "key takeaways", or "in today's rapidly evolving landscape". \
Output the post text only — no preamble, no title, no surrounding quotes."""


def linkedin_post(
    episode: EpisodeScript,
    *,
    today: dt.date | None = None,
    episode_url: str = "",
    api_key: str | None = None,
    model: str = CLAUDE_MODEL,
) -> str:
    """Write the accompanying LinkedIn post for tonight's episode.

    Generated from the same articles the episode used rather than from
    the episode script, so the post can lead on the thing David would
    lead on — which is not always the story that opened the show.
    """
    today = today or dt.date.today()
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    lines = []
    for beat in BEAT_ORDER:
        for item in episode.buckets.get(beat, []):
            body = (item.content or item.summary or "")[:1200]
            lines.append(
                f"[{beat}] {item.title}\n"
                f"  Market: {item.jurisdiction or 'not market-specific'}\n"
                f"  Source: Regulation Asia — {item.url}\n"
                f"  {body}\n"
            )

    link_line = (
        f"Tonight's episode is at: {episode_url}" if episode_url
        else "The episode link will be appended when it publishes — end the "
             "post with a short line pointing to it, without inventing a URL."
    )

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=1200,
        system=LINKEDIN_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Today is {today.strftime('%A %d %B %Y')}.\n\n"
                f"Tonight's episode is titled: {episode.title}\n\n"
                f"{link_line}\n\n"
                "Today's developments:\n\n" + "\n".join(lines)
            ),
        }],
    )
    return "".join(
        b.text for b in response.content if getattr(b, "type", "") == "text"
    ).strip()


BLOG_SYSTEM_PROMPT = """You write the daily companion post for The Asia \
Pacific Evening Update on the TrustSphere blog. It goes up with the episode \
and does one job: tell the reader what Alex and Jordan are talking about \
today, and why it is worth eight minutes.

Alex is the lead host — British, ex-regulator, twenty years of it, reads a \
consultation paper and sees the balance-sheet consequence three years out. \
Jordan is the practitioner — a front-line MLRO who has filed the STRs and sat \
through the inspection, and has no patience for policy that sounds decisive \
and changes nothing on Monday morning. Name them. The post is about their \
conversation, not an anonymous news round-up.

SUBSTANCE — this is a preview with real content in it, not a teaser
For each of the three or four developments the episode covers: what happened, \
what it means for a compliance, risk or financial-crime team in the region, \
and what the hosts make of it. Where Alex and Jordan disagree, say so and say \
what the disagreement is about — that is the most interesting thing you can \
tell a reader, and it is the reason to listen.

A reader who only reads this should come away genuinely informed. A reader \
who then listens should still find the episode worth their time, because the \
hosts argue it out and the post only reports that they do. Never write \
"tune in to find out" or hold back the substance to manufacture a reason to \
listen. Give the facts; the argument is what is worth hearing.

State nothing that is not in the source material or the episode. No invented \
figures, dates or names. Where the source does not say, write that the source \
does not say. Do not put words in Alex's or Jordan's mouths that they do not \
say in the script you are given.

VOICE
Plain, direct, unhurried. British spelling. Short paragraphs. No marketing \
register — no "in today's fast-moving regulatory landscape", no "deep dive", \
no "unpack", no "thrilled", no "key takeaways". Write like a well-informed \
colleague explaining the day, not like a content marketer.

FORMAT — output markdown in exactly this dialect and nothing else:

# Title of the post

*One-sentence standfirst in italics, under 25 words.*

Opening paragraph that states the through-line of the day.

## A heading naming the first development

Two or three short paragraphs.

## A heading naming the second development

Two or three short paragraphs.

Rules for the markdown, which is parsed strictly:
- Exactly one `# ` line, at the top. That is the title.
- `## ` for section headings. Three or four of them.
- Plain paragraphs otherwise, one per line, blank line between.
- `*italics*` only on a whole line of its own.
- Do NOT use bold, inline links, bullet lists, block quotes, tables, code \
blocks, or any markdown other than the above. Links are not supported and \
will render as raw text.
- Around 400 to 600 words in total.

ENDING
Close with a short section headed `## Listen to tonight's episode` \
containing one or two sentences and then the episode URL on its own line, \
exactly as given to you. If no URL is given, write the sentence and omit the \
line — never invent a URL.

Credit Regulation Asia as the source of the day's reporting once, naturally, \
in the body, and point to the Regulation Asia platform for the fuller detail. \
Attribution in the flow of a sentence, not a disclaimer block."""


def blog_post(
    episode: EpisodeScript,
    *,
    today: dt.date | None = None,
    episode_url: str = "",
    api_key: str | None = None,
    model: str = CLAUDE_MODEL,
) -> str:
    """Write the daily TrustSphere blog post for tonight's episode.

    Returns markdown in the dialect `.trustsphere-ricos-builder.js`
    parses — one `# ` title, `## ` headings, plain paragraphs and
    whole-line italics. That builder has no LINK node, so the episode
    URL goes in as a bare line rather than a markdown link, which would
    otherwise render as literal bracket-and-parenthesis text on the
    published page.
    """
    today = today or dt.date.today()
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    lines = []
    for beat in BEAT_ORDER:
        for item in episode.buckets.get(beat, []):
            body = (item.content or item.summary or "")[:1500]
            lines.append(
                f"[{beat}] {item.title}\n"
                f"  Market: {item.jurisdiction or 'not market-specific'}\n"
                f"  Source: Regulation Asia — {item.url}\n"
                f"  {body}\n"
            )

    url_line = (
        f"The episode URL to use verbatim: {episode_url}"
        if episode_url else
        "No episode URL is available yet — omit the URL line."
    )

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=3000,
        system=BLOG_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Today is {today.strftime('%A %d %B %Y')}.\n"
                f"Tonight's episode is titled: {episode.title}\n"
                f"{url_line}\n\n"
                "Here is tonight's episode script. Write the companion post "
                "about this conversation — what Alex and Jordan cover, and "
                "where they disagree. Only attribute views to them that they "
                "actually express here.\n\n"
                "===== EPISODE SCRIPT =====\n"
                f"{episode.body}\n\n"
                "===== THE UNDERLYING REPORTING =====\n"
                "Use this for facts, figures and dates the script refers to "
                "but does not spell out.\n\n" + "\n".join(lines)
            ),
        }],
    )
    return "".join(
        b.text for b in response.content if getattr(b, "type", "") == "text"
    ).strip()


def validate_blog_markdown(md: str) -> list[str]:
    """Check the post against what the Ricos builder can actually render.

    The builder silently degrades anything it does not recognise —
    inline links become literal text, bold markers survive as asterisks
    on the page. Better to catch that here than to read it back off a
    live draft."""
    problems: list[str] = []

    titles = [l for l in md.splitlines() if l.startswith("# ")]
    if len(titles) != 1:
        problems.append(f"expected exactly one '# ' title line, found {len(titles)}")
    elif md.strip().splitlines()[0] != titles[0]:
        problems.append("the '# ' title must be the first line")

    if not [l for l in md.splitlines() if l.startswith("## ")]:
        problems.append("no '## ' section headings")

    for n, line in enumerate(md.splitlines(), 1):
        stripped = line.strip()
        if re.search(r"\[[^\]]+\]\([^)]+\)", stripped):
            problems.append(f"line {n}: inline markdown link will render as raw text")
        if "**" in stripped:
            problems.append(f"line {n}: bold is not supported and will show as asterisks")
        if stripped.startswith(("> ", "```", "|", "1. ")):
            problems.append(f"line {n}: unsupported block type {stripped[:12]!r}")
        if stripped.startswith("#") and not stripped.startswith(("# ", "## ", "### ")):
            problems.append(f"line {n}: heading level not supported by the builder")

    return problems
    """Split TITLE / SUMMARY lines off the top of the model's response."""
    title, summary = "", ""
    lines = text.strip().splitlines()
    body_start = 0
    for i, line in enumerate(lines[:8]):
        stripped = line.strip().lstrip("*# ").strip()
        if stripped.upper().startswith("TITLE:"):
            title = stripped[6:].strip()
            body_start = i + 1
        elif stripped.upper().startswith("SUMMARY:"):
            summary = stripped[8:].strip()
            body_start = i + 1
    body = "\n".join(lines[body_start:]).strip()
    return title, summary, body


def _parse_header(text: str) -> tuple[str, str, str]:
    """Split the TITLE and SUMMARY lines off the top of the response.

    Tolerant of the model decorating them with markdown, since a stray
    '**TITLE:**' should not cost us the episode title."""
    title, summary = "", ""
    lines = text.strip().splitlines()
    body_start = 0
    for i, line in enumerate(lines[:8]):
        stripped = line.strip().lstrip("*# ").strip().rstrip("*").strip()
        if stripped.upper().startswith("TITLE:"):
            title = stripped[6:].strip().strip("*").strip()
            body_start = i + 1
        elif stripped.upper().startswith("SUMMARY:"):
            summary = stripped[8:].strip().strip("*").strip()
            body_start = i + 1
    body = "\n".join(lines[body_start:]).strip()
    return title, summary, body


def generate(
    items,
    *,
    today: dt.date | None = None,
    target_minutes: int | None = None,
    apac_only: bool = False,
    guest: Guest | None = None,
    api_key: str | None = None,
    model: str = CLAUDE_MODEL,
) -> EpisodeScript:
    """Write tonight's episode from Regulation Asia articles."""
    today = today or dt.date.today()
    api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    brief, buckets = build_source_brief(items, today=today, apac_only=apac_only)

    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    # Roughly four tokens per spoken word once speaker tags and line
    # breaks are counted, with headroom. A truncated episode ends
    # mid-sentence and loses the close and the Regulation Asia pointer,
    # so the ceiling is set generously and checked below rather than
    # trusted.
    max_tokens = max(16000, int((target_minutes or 25) * 180 * 4))
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt(target_minutes=target_minutes, guest=guest),
        messages=[{
            "role": "user",
            "content": (
                f"{brief}\n\n"
                f"Write tonight's episode for {today.strftime('%A %d %B %Y')}."
            ),
        }],
    )

    if response.stop_reason == "max_tokens":
        raise RuntimeError(
            f"Episode was truncated at the {max_tokens:,}-token ceiling — it "
            "would air without its close or the Regulation Asia pointer. "
            "Raise max_tokens or lower target_minutes."
        )

    raw = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
    title, summary, body = _parse_header(raw)

    return EpisodeScript(
        title=title or f"APAC Evening Update — {today.isoformat()}",
        summary=summary,
        body=body,
        buckets=buckets,
        usage={
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    )
