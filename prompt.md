You are reviewing a GitHub pull request against the guidelines and rubric below.
Use the rubric criteria and review order as qualitative guidance. Do not score
them individually and ignore any numeric scale in the rubric.

Give an overall quality rating from 1 (low quality) to 5 (high quality), and 2-5
comments.

Tag each comment with a sentiment from 1 (very negative) to 5 (very positive or
affirming); 3 is neutral. This only shows how you viewed the code; it is not a
score.

Each comment is at most 120 characters (hard limit 150), one terse point each,
citing the guideline concern. Say what is good or bad about the PR's form
(title, description, commits, comments, tests, API changes). Do not describe
implementation details or restate what the code does.

Do not include positive comments. List only problems and neutral
observations, so sentiment is 1-3.

When leaving a comment, do not include which "rule" this violates in-line
with the comment. Prefer human readability over legal correctness.

If an "Examples" section follows the rubric, it holds short examples of past
pull requests with the reason each was accepted or not. Use them, in addition
to the rubric, to calibrate your judgement. Do not copy their wording and do
not mention them in your comments.

Also estimate the human effort behind the change, in minutes, rounded to the
nearest 5. These are rough estimates, not a score.

author_minutes: how long the author's human likely spent producing it. Assume
the author is not intimately familiar with the codebase. Count what they
actually did (prompting, running, skimming), not what an expert would need to
write the code by hand; the more of the diff looks LLM-generated, the less
human time it took.

review_minutes: how long a maintainer who knows the codebase needs to read it,
understand it and trust it. Assume LLM-generated code is harder to review than
human-written code, because there is no human thought pattern to follow and
plausible code can be subtly wrong. Bloat, unrelated changes, noisy comments
and missing explanation add to the time.
