Make a web UI for this grader.

## Operation Modes

There should be two modes

- Single PR mode which accepts a link
- Iterative mode, which uses the 30 (10+10+10) model

## Interface 

### Selection

- Selecting the mode (Single or Iterative) on top

If *Single* is selected, then there should be the ability to insert a link
to a single pull request. There should also be a drop-down menu for recent PRs
reviewed by the given user (so the user can iterate). The recent list should
feature the PR number and description/title

If *Iterative* is selected, then there should be the ability to insert a link
to a repo but also select an existing repo

The implementation should create a config file for the repo (and a corresponding
repos/<repo>.md file) if they don't exist. 

### Grading

When the user clicks on "grade", the model runs on the PR
(per the rubrics and normal flow).

### Displaying grade results

The next screen shows the grading results, with annotating the PR
diff with specific comments on what's wrong (only per the rubric).

the PR description should also be displayed with the diffs, using a Markdown
reader

### User's feedback and comments

The user has options to respond with feedback to each comment and the grade in
general. If in iterative mode then the next PR is automatically displayed.

Don't allow feedback types or forms that are not present in plan/grade-review

## User Types

We won't use a user database or authentication model, but the UI should allow
a user to "switch" between user and root. Eventually we will have different
user profiles, but let's keep it simple


## Feedback 
The user can then choose to either apply the proposed changes immediately, or
submit them into a queue for later review. IF the user is not an admin user,
then he cannot apply the changes immediately but would need to place them into
the queue.

## Queue

The queue should contain MD files describing proposed diffs and should be
a directory in the repo root, call it webui-review-queue