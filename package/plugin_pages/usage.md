# Git Panel

The Git panel lets you stage, unstage, and commit changes from inside the Infernux editor, without switching to a terminal.

## Opening the panel

You can find it in the menu bar: `Extensions/Git Integration`.

## Before you start

The panel works on the project folder currently open in the editor. If that folder is not a Git repository yet, the panel shows a **Create Git Repository** view instead of the normal layout. Click **Create Git Repository** to run `git init` on the project folder; the panel then switches to the normal view.

Git must be installed and reachable on your `PATH`. When it is not, the panel shows a short notice instead of the file lists.

## The panel layout

The normal view has four parts, from top to bottom:

- **Source Control** — the header. The `⟳` button on the right forces an immediate `git status`, skipping the refresh interval.
- **Staged Changes** — files that will be included in the next commit.
- **Changes** — files that have been modified or deleted but are not staged yet, plus untracked files.
- **Commit area** — a message box and a **Commit** button.

A file can appear in both lists at once. For example, a file that was staged and then modified again shows up under Staged Changes and under Changes, so you can tell it has both staged and unstaged content.

## Staging and unstaging

- To stage a single file, click the `+` button on its row in **Changes**.
- To stage everything in **Changes** at once, click **Stage all**.
- To unstage a file, click the `−` button on its row in **Staged Changes**. This also works in a repository that has no commits yet.

**Stage all** is equivalent to `git add -A`: it stages modifications, additions, and deletions.

## Committing

- Type a message into the message box. The text stays there while you keep working in the panel.
- Click **Commit**. The commit is created and the file lists refresh right away.
- If the message box is empty, the commit button does nothing — enter a message first.

## Refreshing the file lists

The panel updates the file lists automatically, at most once per second. If you want to see the current state immediately — for example after running Git commands in a terminal — click the `⟳` button in the header.

## Troubleshooting

**The panel reports that Git is not usable.** Git is not installed, or it is not on the `PATH` the Editor was started with. Install Git and restart the Editor.

**Commit does nothing.** The message box is empty. Enter a commit message first.

**`git commit` fails asking who you are.** Git has no identity configured. Run `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`.

**A new file never leaves Changes.** Untracked files are marked `?` until they are staged.

## Upcoming features

Branch display and switching, file status coloring, discard-changes for unstaged files, Push/Pull controls, diff preview, and asynchronous `git status` execution are planned for future versions.
