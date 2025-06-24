# Microbiology Study Suite

A personalized, terminal-based study environment to conquer BIOL2260.


## Nextcloud linkage
ln -s ~/Dev/microbio/notes ~/Nextcloud/vimwiki/microbio
---

---

## Core Tools

This suite leverages powerful command-line tools:

- **Vim/Neovim:** For all text editing.
- **vimwiki:** For linked notes and checklists.
- **nerdtree:** For file system navigation within Vim.
- **fzf:** For fuzzy finding files and notes.
- **flashcard-cli:** For active recall with simple text files.
- **jp2a:** To view images as ASCII art in the terminal.
- **asciiflow:** For creating ASCII diagrams.

---

## Custom Scripts & Aliases

To make using this suite seamless, the following aliases are defined in `~/.bash_aliases` or `~/.zshrc`.

| Command                                           | Description                                                               |
| ------------------------------------------------- | ------------------------------------------------------------------------- |
| `python3 scripts/goal_generator.py`               | Displays today's study priorities based on the `plans/microbiology.yaml`. |
| `python3 scripts/goal_generator.py --wiki`        | Generates a `vimwiki` checklist for today's plan and opens it.            |
| `flashcard-cli $(find flashcards -type f \| fzf)` | Opens a flashcard deck selector using `fzf` to start a session.           |
| `grep -r "" notes/ \| fzf`                        | Fuzzy search for any text within your `notes` directory.                  |
| `python3 scripts/summarize.py`                    | (Future) Summarize a text file using an LLM.                              |
| `python3 scripts/practice_questions.py`           | (Future) Generate practice questions on a topic.                          |

---

## Daily Workflow Example

1.  **Start your session:** Open a terminal in the project directory.
2.  **Generate your plan:** Run `study-wiki`. This will create a checklist in `vimwiki` for today and open it.
3.  **Review notes:** Use `vim` and `nerdtree` or `study-find` to open the relevant chapter notes.
4.  **Practice:** Use `study-cards` to review flashcards for the day's topics.
5.  **Check off items:** As you complete tasks, mark them done in your `vimwiki` daily plan file.
