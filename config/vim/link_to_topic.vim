function! LinkToTopic()
  " Get current word under cursor
  let l:term = expand('<cword>')
  " Normalize: lowercase, remove 's/plurals/punctuation
  let l:clean = substitute(tolower(l:term), "'s\\?\\|s$", '', '')
  let l:clean = substitute(l:clean, '[^a-z0-9_ ]\\+', '', 'g')
  let l:filename = substitute(l:clean, '\s\+', '_', 'g')
  " Collapse multiple underscores into single ones
  let l:filename = substitute(l:filename, '_\\+', '_', 'g')
  " Trim leading and trailing underscores
  let l:filename = substitute(l:filename, '^_\\+', '', '')
  let l:filename = substitute(l:filename, '_\\+$', '', '')
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

function! ExtractToTopic()
  " Yank visual selection into 'z'
  normal! gv"zy
  let l:section = getreg('z')
  if empty(l:section)
    echohl WarningMsg | echo "❌ No text selected." | echohl None
    return
  endif
  
  " Get lines and extract first header line
  let l:lines = split(l:section, "\n")
  let l:header_line = filter(copy(l:lines), 'v:val =~# "^\\s*==.*=="')
  if empty(l:header_line)
    echohl WarningMsg | echo "❌ No valid '== Title ==' line found." | echohl None
    return
  endif
  
  let l:title = substitute(l:header_line[0], '^\\s*==\\s*\\(.*\\)\\s*==\\s*$', '\1', '')
  
  " Make singular (remove possessives and trailing s)
  " More comprehensive singular conversion
  let l:title_singular = l:title
  let l:title_singular = substitute(l:title_singular, "'s\\?", '', 'g')  " Remove possessives
  let l:title_singular = substitute(l:title_singular, '\\cesons$', 'eson', '')  " transposons -> transposon
  let l:title_singular = substitute(l:title_singular, '\\cbacteria$', 'bacterium', '')  " bacteria -> bacterium
  let l:title_singular = substitute(l:title_singular, '\\ces$', '', '')  " processes -> process
  let l:title_singular = substitute(l:title_singular, 's$', '', '')  " general plurals 
 
  " Normalize filename: lowercase, remove non-alphanum except underscores, replace space with _, trim underscores
  let l:filename = substitute(tolower(l:title_singular), '[^a-z0-9_ ]', '', 'g')
  let l:filename = substitute(l:filename, '\s\+', '_', 'g')
  " Collapse multiple underscores into single ones
  let l:filename = substitute(l:filename, '_\+', '_', 'g')
  " Trim leading and trailing underscores
  let l:filename = substitute(l:filename, '^_\+', '', '')
  let l:filename = substitute(l:filename, '_\+$', '', '')
  
  " Handle edge case where filename might be empty after cleaning
  if empty(l:filename)
    echohl WarningMsg | echo "❌ Filename is empty after normalization." | echohl None
    return
  endif
  
  " Create file path
  let l:link = '../../topics/' . l:filename
  let l:file_path = expand('%:p:h') . '/' . l:link . '.wiki'
  
  " Bail if file exists
  if filereadable(resolve(l:file_path))
    echohl WarningMsg | echo "⚠️ File already exists: " . l:filename . ".wiki" | echohl None
    return
  endif
  
  " Write new topic file
  call writefile(l:lines, l:file_path)
  echo "✅ Created topic: " . l:filename . ".wiki"
  
  " Insert Vimwiki link below the selection (do not delete)
  normal! gv`>
  normal! o
  execute "normal! i* [[" . l:link . "|" . l:title . "]]\<Esc>"
  
  silent! execute "UpdateGlossary"
  echo "📚 Glossary updated"
endfunction
xnoremap <leader>et :<C-u>call ExtractToTopic()<CR>
