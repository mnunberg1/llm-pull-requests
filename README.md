# LLM Pull Request Grading Engine

While most review tools are designed to assist machines in grading
human-written code, this project aims to use human review to
establish guardrails around LLM/AI-generated code.

The principal guidelines are in `guidelines.md` which is human-written
(as is this file), and contains do's and don'ts of LLM generated code.
You can try (but I have not yet tried) to feed the guidelines into the
AI for generation, but I mainly wrote this tool to help me _review_ other
people's AI slop code.


# Using

To use this repository, look at plan.md, which contains the project
layout as well as a series of steps designed to generate the folder
layout.

`scripts.md` -- a generated file, is linked in by `plan.md` to
generate the boilerplate which analyzes pull requests and applies the grading.