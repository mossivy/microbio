# Microbiology Study Suite

A personalized, terminal-based study environment to conquer BIOL2260.


## Nextcloud linkage
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

# SCRIPT USAGE

#Glossary Setup add to .vimrc so :UpdateGlossary can be run
command! UpdateGlossary :!bash /PATH/scripts/update_glossary.sh

#In Vim:    :source ~/.vimrc
source ~/PATH/config/vim/link_to_topic.vim
#For autolinking to glossary add this to .vimrc and then reload
usage: <leader>lt
#For selecting == subsection == and creating glossary term
usage: <leader>et

# Generate today's plan (assignments + reviews) 
python study_suite.py --plan-file plans/microbiology.yaml

# Generate in vimwiki format
python study_suite.py --plan-file plans/microbiology.yaml --wiki

# Mark something as reviewed
python study_suite.py --mark-reviewed identification_classification.wiki "Culture Characteristics"

# Check review status
python study_suite.py --status
---

## Daily Workflow Example

1.  **Start your session:** Open a terminal in the project directory.
2.  **Generate your plan:** Run `study-wiki`. This will create a checklist in `vimwiki` for today and open it.
3.  **Review notes:** Use `vim` and `nerdtree` or `study-find` to open the relevant chapter notes.
4.  **Practice:** Use `study-cards` to review flashcards for the day's topics.
5.  **Check off items:** As you complete tasks, mark them done in your `vimwiki` daily plan file.
