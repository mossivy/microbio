function! LinkToTopic()
  " Get current word under cursor
  let l:term = expand('<cword>')

  " Normalize: lowercase, remove 's/plurals/punctuation
  let l:clean = substitute(tolower(l:term), "'s\\?\\|s$", '', '')
  let l:clean = substitute(l:clean, '[^a-z0-9_ ]\\+', '', 'g')
  let l:filename = substitute(l:clean, '\s\+', '_', 'g')
  let l:display = substitute(l:term, '_', ' ', 'g')

  " Determine the path: two levels up from chapter files
  let l:link = '../../topics/' . l:filename
  let l:file_check = expand('%:p:h') . '/../../topics/' . l:filename . '.wiki'

  if filereadable(resolve(l:file_check))
    execute "normal! ciw[[" . l:link . "|" . l:display . "]]"
    echo "✅ Linked to topic: " . l:filename
  else
    echohl WarningMsg | echo "⚠️ Topic not found: " . l:filename . ".wiki" | echohl None
  endif
endfunction

nnoremap <leader>lt :call LinkToTopic()<CR>

