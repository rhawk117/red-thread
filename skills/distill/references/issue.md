# Lens: issue

Reader: maintainers on GitHub. They do not have the case file, so the issue has to stand without it.

Sections the script writes: Summary, Findings (the `known` entries), Open questions, Ruled out, Next steps, References (the `resource` entries), Pointers. Budget: 80 lines.

## Choosing

- `title`: the problem or the proposed change in 70 characters or fewer.
- `goal`: two or three sentences: what is wrong or proposed, and who it affects.
- `include`: the findings that show the problem, the open questions a maintainer can answer, the next steps, and the references worth a click. Leave out how the investigation went.
- `blocking`: leave it out unless an open question blocks the work.

## Checklist

- Each finding has a citation a maintainer can open. A `path:line` is read at the commit named in the first line of the output.
- Nothing private is in it: internal hosts, customer names, anything the owner would not post. The script redacts secret patterns only.
- The first line is the title as a heading. Leave it out of the body when you create the issue.

## Delivering

Creating an issue is public and hard to take back. Ask the owner first with AskUserQuestion, naming the repository, the title and any labels. Then:

```sh
tail -n +3 CASE/out/issue.md | gh issue create --title "TITLE" --body-file -
```

Afterwards record the issue link as a `resource` entry, so the case points at where the work went.
