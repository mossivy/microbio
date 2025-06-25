function! LinkToTopic()
  let l:term = expand('<cword>')
  let l:wiki_root = finddir('notes', ';')
  if empty(l:wiki_root)
    echohl ErrorMsg | echo "Couldn't find notes/ directory" | echohl None
    return
  endif

  " Convert term to lowercase snake_case
  let l:filename = tolower(substitute(l:term, '\s\+', '_', 'g'))
  let l:topic_path = l:wiki_root . '/topics/' . l:filename . '.wiki'

  if filereadable(l:topic_path)
    " Insert link at cursor position
    execute 'normal! i[[../topics/' . l:filename . '|' . l:term . ']]'
  else
    echohl WarningMsg | echo "No topic file for '" . l:term . "' found." | echohl None
  endif
endfunction

" Keybinding: Leader + l then t
nnoremap <leader>lt :call LinkToTopic()<CR>

