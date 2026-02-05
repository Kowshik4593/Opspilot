
EMAIL_SUMMARY_PROMPT = """Summarize the email in a brief paragraph (2-3 sentences). Focus on:
- What is being asked or requested
- Any deadlines or time-sensitive items
- Key people mentioned and their roles

Write in plain prose, NOT in JSON or bullet points. Be concise and professional.

Email:
Subject: {subject}
Body: {body}
"""

EMAIL_ACTIONS_PROMPT = """From the email, extract explicit action items as JSON array with fields:
title, owner_email (if explicit), due_date_utc (ISO if implied). Be precise.
Email:
Subject: {subject}
Body: {body}
"""

EMAIL_REPLY_PROMPT = """Write a concise, professional reply in a {tone} tone. Include a short next-steps list and close with the user's signature.
Context:
- Sender: {from_email}
- Subject: {subject}
- Email body: {body}
Signature:
{signature}
"""

MOM_PROMPT = """You are an expert Meeting Intelligence agent creating detailed Minutes of Meeting (MoM).

Analyze the transcript carefully and extract SPECIFIC, DETAILED information. DO NOT use generic phrases.

Return a STRICT JSON object with these keys:
- summary (string): 3-5 sentences capturing the main discussion topics, key participants, and overall outcome. Be SPECIFIC about what was discussed.
- decisions (array of strings): Each decision should be a complete, specific statement. Include WHO decided, WHAT was decided, and any numbers/dates mentioned.
- action_items (array of strings): Each item should include: WHAT needs to be done, WHO is responsible (if mentioned), and WHEN (deadline if mentioned). Be specific!
- risks (array of strings): Specific risks mentioned with context. Include impact if discussed.
- dependencies (array of strings): External dependencies, blockers, or things needed from others.

CRITICAL RULES:
1. Extract ACTUAL content from the transcript - no generic placeholders
2. Include specific names, numbers, dates, and technical details mentioned
3. If someone says "I'll send X by Friday" → action item: "[Person] to send X by Friday"
4. If a specific decision was made → include the actual decision with details
5. Quote key metrics, costs, timelines mentioned (e.g., "$500k budget", "4-5 months", "99.97% uptime")
6. No markdown, no code fences - return ONLY valid JSON
7. If nothing found for a section, return empty array []

Transcript:
{transcript}
"""

NUDGE_PROMPT = """
You are generating a short follow‑up nudge based on a specific task.

Return a brief, friendly‑professional message in less than 60 words.
The message MUST be specific — use the task title, due date, priority, and status.

DO NOT use generic text like "this item is due soon".

Rules:
- NO markdown, NO bold, NO asterisks. Plain text only.
- Message must be under 60 words.
- Use the task title, priority, status, and due date.
- Tone should be polite and professional.
- If overdue, call it out clearly but gently.

Content requirements:
- Mention the task title clearly.
- Mention due date (if available) and status.
- Mention owner politely.
- Ask for a short update.
- If overdue, call it out politely (e.g., "was due on ...").

Input:
Task Title: {title}
Priority: {priority}
Status: {status}
Due Date: {due_date}
Reason: {reason}
Recommended Channel: {channel}
Owner: {owner}
"""

EOD_PROMPT = """Craft a crisp end-of-day summary based on tasks and followups. Include Completed, In Progress, Pending highlights and mention risks if any.
Data:
- completed: {completed}
- in_progress: {in_progress}
- pending: {pending}
- followups: {followups}
"""

# ============================================================
# WELLNESS AGENT PROMPTS
# ============================================================

WELLNESS_ANALYSIS_PROMPT = """Analyze the employee's current workload and wellness indicators.

Current Workload:
- P0 (Critical) Tasks: {p0_count}
- P1 (High) Tasks: {p1_count}
- Overdue Tasks: {overdue_count}
- Meetings Today: {meeting_hours} hours
- Actionable Emails: {email_count}
- Pending Follow-ups: {followup_count}
- Longest Focus Block: {focus_minutes} minutes

Provide a brief, empathetic wellness assessment (2-3 sentences) that:
1. Acknowledges their current load honestly
2. Identifies the biggest stress factor
3. Offers one actionable suggestion

Keep it supportive and professional. No markdown formatting.
"""

BURNOUT_DETECTION_PROMPT = """Assess burnout risk based on these 5-day patterns:

Workload Signals:
{signals}

Evaluate and provide:
1. Risk level (low/medium/high/critical)
2. Top 3 warning signs observed
3. 2-3 specific, actionable recommendations

Be direct but supportive. Focus on operational changes, not medical advice.
Return plain text, no markdown.
"""

BREAK_SUGGESTION_PROMPT = """The employee has been working for {work_duration} and needs a break suggestion.

Current context:
- Time of day: {time_of_day}
- Work intensity: {intensity}
- Upcoming commitments: {upcoming}

Suggest ONE specific break activity (30 words max) that's:
- Appropriate for office environment
- Quick and refreshing
- Specific (not generic)

Return just the suggestion, no preamble.
"""

FOCUS_PLAN_PROMPT = """Create a focused work plan for the employee.

Available time slots:
{time_slots}

Priority tasks:
{priority_tasks}

Create 2-3 focus blocks with:
- Specific time windows
- Which task to work on
- Brief rationale

Keep it actionable and realistic. Plain text, no markdown.
"""

MEETING_DETOX_PROMPT = """Analyze today's meetings for optimization opportunities.

Meetings:
{meetings}

Current workload pressure: {pressure_level}

Identify meetings that could be:
- Declined (with suggested reason)
- Delegated (suggest who)
- Made async (suggest format)
- Shortened (suggest new duration)

Only suggest changes that make sense. Be specific about why.
Plain text, no markdown.
"""

MOOD_RESPONSE_PROMPT = """The employee reported feeling: {mood}

Their current situation:
- Open tasks: {task_count} ({p0_count} critical)
- Meetings today: {meeting_count}
- Overdue items: {overdue_count}

Provide a brief, empathetic response (2-3 sentences) that:
1. Validates their feeling
2. Acknowledges their workload
3. Suggests one small, immediate action

Be warm but professional. No toxic positivity. Plain text only.
"""

CELEBRATION_PROMPT = """The employee just completed: {task_title}

Task details:
- Priority: {priority}
- Was overdue: {was_overdue}
- Time spent: {time_spent}

Generate a brief celebration message (1-2 sentences) that:
- Acknowledges the specific accomplishment
- Is genuine, not over-the-top
- Optionally suggests what's next

Keep it natural and professional. Plain text only.
"""
