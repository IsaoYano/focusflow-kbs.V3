# tools.py
# ================================================================
# The 4 Procedural Knowledge Tools for FocusFlow-KBS
# Each @tool function represents one specific expert intervention.
# The agent DECIDES which tool to call based on user input.
# ================================================================

from langchain_core.tools import tool
import re


# ---------------------------------------------------------------
# HELPER FUNCTION: SAFE EMOTIONAL INTENSITY EXTRACTION
# Prevents time values like "2am" from being read as intensity 2/10.
# ---------------------------------------------------------------
def extract_emotional_intensity(text: str):
    """
    Extract emotional intensity only when the number is clearly linked
    to stress/emotion wording. This prevents mistakes like reading '2am'
    as emotional intensity 2/10.
    """
    text = str(text)

    patterns = [
        # Examples: stressed 9/10, stress level 9/10, intensity: 9/10
        r"\b(?:emotional_intensity|emotion|emotional intensity|stress|stressed|stress level|anxiety|anxious|overwhelmed|overwhelm|intensity)\s*(?:is|=|:|at|level)?\s*(\d{1,2})\s*/\s*10\b",

        # Examples: stressed 9, anxiety 8, overwhelmed 7
        r"\b(?:emotional_intensity|emotion|emotional intensity|stress|stressed|stress level|anxiety|anxious|overwhelmed|overwhelm|intensity)\s*(?:is|=|:|at|level)?\s*(\d{1,2})\b",

        # Examples: 9/10 stressed, 8/10 anxiety
        r"\b(\d{1,2})\s*/\s*10\s*(?:stress|stressed|anxiety|anxious|overwhelmed|overwhelm|emotion|emotional intensity|intensity)\b",

        # Examples: I feel 9/10, feeling at 8/10
        r"\b(?:feel|feeling|felt)\s*(?:like|at)?\s*(\d{1,2})\s*/\s*10\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if 1 <= value <= 10:
                return value

    stress_words = [
        "stressed", "stress", "overwhelmed", "overwhelm",
        "anxious", "anxiety", "panicking", "panic",
        "frustrated", "scared", "freaking out"
    ]

    if any(word in text.lower() for word in stress_words):
        return 7

    return None


# ---------------------------------------------------------------
# TOOL 1: EMOTIONAL CHECK-IN TOOL
# This is the HIGHEST PRIORITY tool.
# Called first whenever emotional intensity >= 6/10.
# ---------------------------------------------------------------
@tool
def emotional_checkin_tool(tool_input: str) -> str:
    """
    Assesses emotional state and provides regulation strategies BEFORE task planning.
    PRIORITY: HIGHEST — always call this before any other tool if emotion >= 6/10.
    USE WHEN: User says overwhelmed, stressed, anxious, panicking, frustrated, or scared.
    INPUT: full user situation as text. The tool will extract emotional intensity if available.
    """
    text = str(tool_input)

    # Extract emotional intensity safely.
    # This avoids reading time values like "2am" as emotional intensity.
    emotional_intensity = extract_emotional_intensity(text)

    if emotional_intensity is None:
        emotional_intensity = 7

    emotion_description = text

    if emotional_intensity >= 8:
        strategy = """
HIGH INTENSITY DETECTED — Complete ALL steps before any task work:

STEP 1 — BOX BREATHING (3 minutes):
  Breathe IN for 4 counts... HOLD for 4 counts...
  Breathe OUT for 4 counts... HOLD empty for 4 counts.
  Repeat this 4 full times.

STEP 2 — PHYSICAL RESET (2 minutes):
  Stand up. Roll shoulders backwards 5 times.
  Shake out your hands for 10 seconds.
  Drink a full glass of water.

STEP 3 — GROUNDING (1 minute):
  Name 5 things you can SEE around you.
  Name 4 things you can TOUCH.
  Name 3 things you can HEAR.

STEP 4 — RE-CHECK:
  Rate your intensity again (1-10).
  If still above 7: Repeat Steps 1-3 once more.
  If 6 or below: You are ready for task planning.

DO NOT PROCEED TO TASK PLANNING UNTIL INTENSITY IS BELOW 7."""

    elif emotional_intensity >= 6:
        strategy = """
MODERATE INTENSITY — Quick regulation before continuing:

QUICK RESET (2 minutes):
  1. Take 5 slow deep breaths (breathe out for longer than in).
  2. Drink some water.
  3. Say quietly: "I can handle this one step at a time."

RE-CHECK:
If still 6 or above, do the full box breathing above.
If 5 or below, you are ready to continue."""

    else:
        strategy = """
MANAGEABLE STATE — Ready to plan tasks.
Quick check: Take 3 slow breaths before we begin.
You are doing well by reaching out for support."""

    return f"""
EMOTIONAL CHECK-IN RESULT
Task: {emotion_description}
Intensity: {emotional_intensity}/10

{strategy}

EVIDENCE BASE:
"Yoga/exercise offers strategies to increase attention and emotion
regulation skills, which are core to ADHD."
Source: Albalawi et al. (2026), Lines 978-986. SMD=0.84. Rule A-005, CF: 0.75.

"CBT addressing: problem-solving, self-control, dealing with feelings."
Source: NICE NG87 (2019), Slide 21, Recommendation 1.5.14. Rule N-004, CF: 0.85.

IMPORTANT: FocusFlow provides support strategies only.
For persistent emotional difficulties, consult a mental health professional.
"""


# ---------------------------------------------------------------
# TOOL 2: TASK CHUNKING TOOL
# Breaks long tasks into 25-minute segments with 5-minute breaks.
# Called when task duration > 60 minutes.
# ---------------------------------------------------------------
@tool
def task_chunking_tool(tool_input: str) -> str:
    """
    Breaks a large task into manageable time segments with scheduled breaks.
    USE WHEN: Task duration is more than 60 minutes, OR task described as large, overwhelming, or huge.
    INPUT: full user situation as text. The tool will extract task duration if available.
    """
    text = str(tool_input)

    task_description = text
    task_type = "general"

    # Extract duration from patterns like "90 min", "2 hours", "3-hour", "2500-word"
    minute_match = re.search(r"(\d{1,3})\s*(?:min|mins|minute|minutes)", text, re.IGNORECASE)
    hour_match = re.search(r"(\d{1,2})\s*(?:hour|hours|hr|hrs)", text, re.IGNORECASE)
    word_match = re.search(r"(\d{3,5})\s*(?:word|words)", text, re.IGNORECASE)

    if minute_match:
        duration_minutes = int(minute_match.group(1))
    elif hour_match:
        duration_minutes = int(hour_match.group(1)) * 60
    elif word_match:
        # Rough estimate: 500 words = about 60 minutes for planning/writing
        words = int(word_match.group(1))
        duration_minutes = max(60, round(words / 500 * 60))
    else:
        return f"""
TASK CHUNKING NEEDS ONE CLARIFICATION
Task: {task_description}

I should not assume the task duration.
Before I create a schedule, please estimate one of these:
- how many minutes/hours you want to work, or
- how much is left, such as one section, half done, or not started.

Reason: A task schedule should be based on the user's actual time or remaining workload, not a default estimate.
[Source: Rule A-001, Albalawi et al. (2026), CF: 0.85; Rule R-002, Ramos-Galarza et al. (2024), CF: 0.80]
"""

    duration_minutes = max(15, min(duration_minutes, 240))
    chunk_size = 25    # Minutes of focused work per segment
    break_size = 5     # Minutes of rest between segments
    major_break = 15   # Minutes for a major rest at midpoint if over 90 min

    schedule_lines = []
    remaining = duration_minutes
    segment_number = 1
    total_elapsed = 0
    halfway_done = False

    while remaining > 0:
        # Add a major break at approximately halfway through long sessions
        if not halfway_done and total_elapsed >= (duration_minutes / 2) and total_elapsed >= 45:
            schedule_lines.append(f"  MAJOR BREAK: {major_break} minutes — Walk, eat, drink water")
            total_elapsed += major_break
            halfway_done = True

        work_time = min(chunk_size, remaining)
        schedule_lines.append(f"  Segment {segment_number}: {work_time} min — {task_description}")
        total_elapsed += work_time
        remaining -= work_time
        segment_number += 1

        if remaining > 0:
            schedule_lines.append(f"  Mini-break: {break_size} min — Breathe, stretch, move")
            total_elapsed += break_size

    schedule_text = "\n".join(schedule_lines)
    num_segments = segment_number - 1

    return f"""
TASK CHUNKING PLAN
Task: {task_description}
Type: {task_type}
Original Duration: {duration_minutes} minutes
Work Segments: {num_segments}
Total Session Time Including Breaks: approximately {total_elapsed} minutes

YOUR SCHEDULE:
{schedule_text}

HOW TO USE THIS:
Set a timer for {chunk_size} minutes. Work until it rings.
Then stop — even if you are in the middle of something.
Take your break. Then set the timer again.

EVIDENCE BASE:
"Organizational skills training aims to build organization and time management skills
in children with ADHD. Children use daily planners, to-do lists, or tasks that are
broken into parts."
Source: Albalawi et al. (2026), Lines 395-398. Rule A-001, CF: 0.85.

"Section 504 provides: clear direction for homework, dividing tests into small
multiple tests, increasing time for test completion."
Source: Albalawi et al. (2026), Lines 371-374. Rule A-002, CF: 0.90.
"""


# ---------------------------------------------------------------
# TOOL 3: PRIORITY TRIAGE TOOL
# Helps users decide task order when they have multiple tasks.
# Called when 2 or more tasks are mentioned.
# ---------------------------------------------------------------
@tool
def priority_triage_tool(tasks_description: str) -> str:
    """
    Helps prioritize multiple tasks using an urgency and difficulty matrix.
    USE WHEN: User mentions 2 or more tasks, asks what to do first, or describes a group project coordination problem.
    INPUT: tasks_description as text describing all the tasks.
    """
    lower_tasks = tasks_description.lower()
    group_project_note = ""

    if any(keyword in lower_tasks for keyword in [
        "group project", "group assignment", "team project", "teammate",
        "team member", "group member", "person in charge", "not replying"
    ]):
        group_project_note = """
GROUP PROJECT COORDINATION NOTE:
Because this task depends on other people, separate what you can control from what needs a team response.

1. Write down the part you can complete independently.
2. Send one clear message to the group with a specific request and deadline.
3. If nobody replies, continue the part you can complete and keep proof of your messages/progress.
4. If needed, update the lecturer or person in charge with factual evidence, not emotion.

Evidence link: Rule A-008, CF: 0.75.
"""

    return f"""
PRIORITY TRIAGE ANALYSIS
Tasks described: {tasks_description}
{group_project_note}

PRIORITY FRAMEWORK — Urgency multiplied by Difficulty:

TIER 1 — DO FIRST (Urgent + Easy):
  These tasks are due soon AND relatively quick.
  Complete them first. Quick wins build momentum for harder tasks.

TIER 2 — DO SECOND (Urgent + Hard):
  These are due soon AND require significant effort.
  Tackle them when your energy and focus are freshest.
  Allocate the most time here.

TIER 3 — DO THIRD (Not Urgent + Easy):
  These are not due immediately and are manageable.
  Fill shorter time gaps with these tasks.

TIER 4 — START EARLY (Not Urgent + Hard):
  Not due immediately but will take significant effort.
  Do NOT wait until the deadline approaches.
  Begin breaking these into small subtasks now.

HOW TO APPLY THIS TO YOUR TASKS:
  Step 1: For each task, ask: Is it due today or tomorrow? (Urgent) Or later? (Not Urgent)
  Step 2: For each task, ask: Is it quick and simple? (Easy) Or complex? (Hard)
  Step 3: Place each task into one of the 4 tiers above.
  Step 4: Work through Tier 1 first, then 2, then 3.

EVIDENCE BASE:
"Boyer et al. demonstrated that the planning skills the child develops through
CBT improve symptoms."
Source: Albalawi et al. (2026), Lines 384-386. Rule A-003, CF: 0.75.

"CBT addressing: problem-solving, self-control."
Source: NICE NG87 (2019), Slide 21, Recommendation 1.5.14. Rule N-004, CF: 0.85.

"Peer-mediated or social-context strategies can support group-task coordination when ADHD-related planning and social participation difficulties affect collaborative work."
Source: Albalawi et al. (2026). Rule A-008, CF: 0.75.
"""


# ---------------------------------------------------------------
# TOOL 4: DISTRACTION CONTROL TOOL
# Gives specific environmental changes to reduce distractions.
# Called when user reports high or medium distraction.
# ---------------------------------------------------------------
@tool
def distraction_control_tool(tool_input: str) -> str:
    """
    Recommends specific environmental modifications to reduce distractions.
    USE WHEN: User mentions noise, phone distractions, siblings, cannot focus.
    INPUT: full user situation as text. The tool will classify distraction level.
    """
    text = str(tool_input)
    environment_details = text

    high_keywords = [
        "very noisy", "too noisy", "ragebait", "scrolling", "phone",
        "cannot focus", "can't focus", "distracted", "high distraction"
    ]
    medium_keywords = ["some noise", "medium distraction", "notifications", "people around"]

    lower_text = text.lower()

    if any(keyword in lower_text for keyword in high_keywords):
        distraction_level = "high"
    elif any(keyword in lower_text for keyword in medium_keywords):
        distraction_level = "medium"
    else:
        distraction_level = "low"

    if distraction_level.lower() == "high":
        actions = [
            "PHONE: Turn off ALL notifications. Place phone in another room entirely.",
            "SOUND: Use noise-cancelling headphones with white noise or soft instrumental music.",
            "LOCATION: Move to the quietest room available. Close the door.",
            "SCREEN: Close every browser tab except what is needed for this specific task.",
            "DESK: Remove everything from your desk except the materials for this task.",
            "PEOPLE: Tell anyone nearby: 'I need uninterrupted time for the next X minutes.'",
        ]
    elif distraction_level.lower() == "medium":
        actions = [
            "PHONE: Activate Do Not Disturb mode.",
            "SOUND: Consider headphones with background music.",
            "SCREEN: Close social media and entertainment tabs.",
            "DESK: Clear the main workspace area.",
        ]
    else:
        actions = [
            "Your environment is manageable.",
            "Quick check: Are any notifications on? Silence them.",
            "Quick check: Any unnecessary tabs open? Close them.",
        ]

    actions_text = "\n".join([f"  {action}" for action in actions])

    return f"""
DISTRACTION CONTROL PLAN
Distraction Level: {distraction_level.upper()}
Environment: {environment_details}

ACTIONS TO TAKE NOW (before starting work):
{actions_text}

TIME REQUIRED FOR SETUP: approximately 3 to 5 minutes.
This investment prevents 20 to 30 minutes of lost focus.

THE KEY PRINCIPLE:
For ADHD brains, external stimuli actively compete for limited attention.
It is significantly more effective to remove distractions before starting
than to try to ignore them while working.

EVIDENCE BASE:
"Environmental modifications to reduce the impact of ADHD symptoms."
Source: NICE NG87 (2019), Slide 14, Recommendation 1.4.3. Rule N-001, CF: 0.90.

"Section 504 provides specific facilities to the child, like providing a quiet place."
Source: Albalawi et al. (2026), Lines 371-374. Rule A-002, CF: 0.90.
"""
