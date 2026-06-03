---
name: swsd-comment-style
description: Draft, revise, or post SolarWinds Service Desk incident comments in James Davis's usual ICT support style. Use when the user asks to write, polish, suggest, add, or post an SWSD incident comment; reply to a requester; add a private/internal incident note; summarize next steps for a ticket; or convert a technical finding into a Service Desk comment.
---

# SWSD Comment Style

## Core Rule

Use this skill for incident comments written as James Davis. Fetch the incident and recent comments first when a ticket number or incident ID is provided. Draft first unless the user explicitly asks to post/add the comment.

Do not post as another person unless the tool/API explicitly attributes the comment to that person and the user clearly requested it.

## Workflow

1. Resolve the ticket identity.
   - If the user gives a visible ticket number like `#23148`, search/list first if direct fetch may confuse visible number with internal ID.
   - Verify the incident's `number` field before acting.
2. Read enough context.
   - Fetch the incident record.
   - Fetch recent comments when writing a response, closing note, or follow-up.
   - Identify requester, state, priority, category, current assignee, and the actual ask.
3. Decide comment type.
   - Public/user-facing: visible to requester; use polished but practical wording.
   - Private/internal: hidden from requester; use concise operational notes, evidence, commands, and rationale.
4. Draft the comment.
   - If the user asks to "write", "draft", "suggest", or "what should I say", do not post.
   - If the user explicitly asks to "add", "post", "comment", or "reply", post using the appropriate SWSD tool.
   - For ambiguous side-effecting requests, draft and ask for confirmation.
5. Report the result.
   - If posted, include ticket number, comment visibility, comment ID when available, and any updated fields.
   - If drafted, clearly label it as a draft.

## User-Facing Voice

Write in a practical, calm school ICT support tone. Be concise, direct, and helpful. Avoid corporate helpdesk language.

Default shape:

```text
Hi [Name],

[Plain update, action taken, or direct question.]

[Optional next step or workaround.]

Thanks,
James
```

Use `Regards, James` for more formal vendors, executives, or completed administrative/security work. Use `Thanks, James` for normal staff/student support.

Style rules:

- Use first person singular naturally: "I've", "I can", "I just".
- Say what happened or what is needed next.
- Ask one clear next-step question where possible.
- Give realistic time estimates when asking to troubleshoot.
- Prefer "Can you please..." and "Do you have some time..." over commands.
- Use "Thanks for..." when acknowledging user effort or patience.
- Be transparent when correcting yourself: "Sorry, I just re-read this..."
- Include exact systems, accounts, roles, URLs, or commands when useful.
- Keep routine replies short.

Common phrases:

```text
Can you please confirm...
Can you please try again?
Let me know if you still need some help.
Do you have some time today...
Thanks for your patience with this.
This has now been actioned.
This has now been reverted to the previous time.
```

## Technical User Comments

When giving a workaround:

- Give the exact command or steps.
- Keep framing short.
- Make temporary workarounds clear.
- Avoid deep diagnosis unless the user needs it.

Example:

```text
Hi [Name],

Thanks for the feedback. We're continuing the investigation with [vendor/support]. In the meantime, feel free to keep using this command in Terminal as a workaround:

[command]

Regards,
James
```

When asking for hands-on troubleshooting:

```text
Hi [Name],

Do you have some time today for me to confirm whether this is related to [known issue]? I'm happy to come to you or you can come by ICT. It should take approximately [time].

Thanks,
James
```

## Private/Internal Notes

Private notes can be short, candid, and operational. They do not need greeting/sign-off unless they are written to another agent/team member.

Use private notes for:

- Findings and evidence.
- Commands or exact system output.
- Internal rationale.
- Next-step reminders.
- Risk/impact notes.
- Ticket hygiene.

Examples:

```text
Needs to be done for T3
Leaving open to make sure [dependency] happens.
Arrange time to see her in person to verify [thing].
[system/tool output pasted for record]
```

For technical analysis notes:

- Start with likely meaning or hypothesis.
- Use bullets for possibilities.
- Use numbered troubleshooting layers when the issue is complex.
- Include exact URLs, commands, policy names, logs, and evidence to collect.
- End with the recommended first move.

## Public Vs Private Safety

Before posting a public comment, remove or avoid:

- Internal uncertainty that should not be visible.
- Sensitive security details beyond what the requester needs.
- Credentials, tokens, secrets, private URLs, and raw logs.
- Comments about colleagues or internal process friction.
- Vendor or product criticism that is not useful to the requester.

Before posting a private comment, mark it private with the dedicated private-comment tool where available. Do not rely on body text saying "private".

## Posting With SWSD Tools

Use `swsd_create_private_incident_comment` for private comments.

For public comments, use the available SWSD incident comment creation tool if present. If only the private-comment tool is available, do not post a public comment; draft it and explain that the current tool only creates private comments.

When updating incident fields at the same time, verify the final incident after posting/updating if the outcome matters.

## Avoid

- "We apologize for the inconvenience."
- Generic macro language.
- Long reassurance.
- Overly polished corporate phrasing.
- Multiple unfocused questions.
- Posting when the user only asked for a draft or suggestion.
