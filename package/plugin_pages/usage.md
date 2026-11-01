# Git Panel

The Git panel lets you stage, unstage, and commit changes from inside the Infernux editor, without switching to a terminal.

## Opening the panel

You can find it in the menu bar: `Extensions/Git Integration`.

## Before you start

The panel works on the project folder currently open in the editor. If that folder is not a Git repository yet, the panel shows a **Create Git Repository** view instead of the normal layout. Click **Create Git Repository** to run `git init` on the project folder; the panel then switches to the normal view.

Git must be installed and reachable on your `PATH`. When it is not, the panel shows a short notice instead of the file lists.

## The panel layout

The normal view has five parts, from top to bottom:

- **Source Control** — the header. The refresh icon on the right forces an immediate `git status`, skipping the refresh interval.
- **Branches** — the branch the project is on, the list of branches, and the row that creates a new one.
- **Staged Changes** — files that will be included in the next commit.
- **Changes** — files that have been modified or deleted but are not staged yet, plus untracked files.
- **Commit area** — a message box and a **Commit** button.

A file can appear in both lists at once. For example, a file that was staged and then modified again shows up under Staged Changes and under Changes, so you can tell it has both staged and unstaged content.

## Reading a file row

Each file row carries three pieces of information:

- **A status icon** for the kind of change: added, modified, deleted, renamed, copied, conflicted, untracked, or ignored.
- **The file path.**
- **The Git status code**, in the colour of that change — added is green, modified is yellow, deleted is red, untracked is cyan, renamed is blue, and a conflict is orange. The code keeps its Git spelling, so a dual state such as `AM` stays readable. Hover it for the name of the change.

At the end of the row sits the action button for that file.

## Staging and unstaging

- To stage a single file, click the `+` icon on its row in **Changes**.
- To stage everything in **Changes** at once, click **Stage all**.
- To unstage a file, click the `−` icon on its row in **Staged Changes**. This also works in a repository that has no commits yet.

**Stage all** is equivalent to `git add -A`: it stages modifications, additions, and deletions.

## Committing

- Type a message into the message box. The text stays there while you keep working in the panel.
- Click **Commit**. The commit is created and the file lists refresh right away.
- If the message box is empty, the commit button does nothing — enter a message first.

## Refreshing the file lists

The panel updates the file lists automatically, at most once per second. If you want to see the current state immediately — for example after running Git commands in a terminal — click the refresh icon in the header.

## Switching branches

The **Branches** section of the panel holds everything about branches. It opens the first time you open the panel, and you can fold it away like the file lists.

- The first line is the branch the project is currently on, together with its upstream and how far it has drifted from it (`↑2 ↓1`).
- The list below shows the local branches first and the remote ones after them. The current branch is marked with a dot, and a branch that tracks another one shows its upstream on the right.
- Type in the filter box to narrow the list down. The filter only changes what is shown; it runs no command.
- Click a branch to select it. The selected branch is marked with an arrow, and the actions below the list apply to it.
- **Checkout** switches to the selected branch. The switch runs in the background, so the panel stays responsive even in a large repository.
- **Rename** opens a field for the new name. The name is checked before it is used, and a branch name may contain `/`, for example `feature/new-panel`.
- **Delete** removes the selected branch. Git refuses to delete a branch whose commits were never merged; **Force delete** removes it anyway, and the commits stay in git's reflog.
- Type a name in the field at the bottom and click **Create** to make a branch from the current commit and switch to it.

If a switch fails — usually because the working tree has changes that the other branch would overwrite — a dialog explains what went wrong in one sentence and points at the Console, which is where the full Git message is kept. The dialog offers **Open Console**, **Copy details**, and **Close**.

## Troubleshooting

**The panel reports that Git is not usable.** Git is not installed, or it is not on the `PATH` the Editor was started with. Install Git and restart the Editor.

**Commit does nothing.** The message box is empty. Enter a commit message first.

**`git commit` fails asking who you are.** Git has no identity configured. Run `git config --global user.name "Your Name"` and `git config --global user.email "you@example.com"`.

**A new file never leaves Changes.** Untracked files are marked `?` until they are staged.

**The icons are missing.** The icons are vector artwork that the Editor rasterizes when the panel first opens. If the Editor was started without GPU support, or the textures could not be uploaded, the panel falls back to text-only controls and the status codes still work.

**An operation fails and the panel looks unchanged.** The panel writes the reason to the Editor Console. Open the Console window to read it — the full Git output is kept there, so it stays available after the message box closes.

## Licences

The plugin ships its own licence and the notices for the icon artwork with the plugin itself. Open the **License** tab of this plugin to read them.

The panel icons come from Lucide, which is free for commercial use. The editor draws plugin pages as plain text, so the links below are written out in full:

https://github.com/Wokrlie/InxGitIntegration/blob/main/package/plugin_pages/license.md

The plugin's own MIT licence:

https://github.com/Wokrlie/InxGitIntegration/blob/main/LICENSE

## Upcoming features

Discard-changes for unstaged files, Push/Pull controls, and diff preview are planned for future versions.
