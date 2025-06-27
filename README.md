# Microbiology Study Suite

A personalized, terminal-based study environment to conquer BIOL2260.

## Core Tools

This suite leverages powerful command-line tools:

- **Vim/Neovim:** For all text editing.
- **vimwiki:** For linked notes and checklists.
- **nerdtree:** For file system navigation within Vim.
- **fzf:** For fuzzy finding files and notes.
- **flashcard-cli:** For active recall with simple text files.
- **asciiflow:** For creating ASCII diagrams.
- **viu + kitty**: For viewing images in the terminal

---

# SCRIPT USAGE

# Glossary Setup add to .vimrc so :UpdateGlossary can be run
command! UpdateGlossary :!bash /PATH/scripts/update_glossary.sh

# In Vim:    :source ~/.vimrc
source ~/PATH/config/vim/link_to_topic.vim
# For autolinking to glossary add this to .vimrc and then reload
usage: <leader>lt
# For selecting == subsection == and creating glossary term
usage: <leader>et
# For surrounding visual section with [ [ ] ] for linking
usage: <leader>[

# Generate today's plan (assignments + reviews) 
python3 scripts/glossary_planner.py

# Generate metadata for terms/topics in glossary
python3 scripts/glossary_study_manager.py generate


# Daily Workflow Example

1.  **Start your session:** Open a terminal in the project directory.
2.  **Generate your plan:** Run `study-wiki`. This will create a checklist in `vimwiki` for today and open it.
3.  **Review notes:** Use `vim` and `nerdtree` or `study-find` to open the relevant chapter notes.
4.  **Practice:** Use `study-cards` to review flashcards for the day's topics.
5.  **Check off items:** As you complete tasks, mark them done in your `vimwiki` daily plan file.
