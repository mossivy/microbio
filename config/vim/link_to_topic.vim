function! LinkToTopic(...)
  " Check if we got text as an argument (from visual mode)
  if a:0 > 0 && !empty(a:1)
    let l:term = a:1
    let l:was_visual = 1
    echo "DEBUG: Got text from argument: '" . l:term . "'"
  else
    " No argument, use current word
    let l:term = expand('<cword>')
    let l:was_visual = 0
    echo "DEBUG: No argument, using word under cursor: '" . l:term . "'"
  endif

  " Debug output
  echo "DEBUG: Captured term: '" . l:term . "'"
  echo "DEBUG: Was visual: " . l:was_visual

  if empty(l:term)
    echohl WarningMsg | echo "❌ No text selected or no word under cursor." | echohl None
    return
  endif

  " Use the original term for display in the link
  let l:display = l:term

  " --- FILENAME NORMALIZATION ---
  " 1. Start with the lowercase version of the term
  let l:filename = tolower(l:term)

  " 2. Remove characters that are NOT alphanumeric or spaces
  let l:filename = substitute(l:filename, '[^a-z0-9 ]', '', 'g')

  " 3. Collapse multiple spaces into a single space
  let l:filename = substitute(l:filename, '\s\+', ' ', 'g')

  " 4. Trim leading/trailing spaces
  let l:filename = substitute(l:filename, '^\\s\\+', '', '')
  let l:filename = substitute(l:filename, '\\s\\+$', '', '')

  " Handle edge case where filename might be empty after cleaning
  if empty(l:filename)
    echohl WarningMsg | echo "❌ Filename is empty after normalization." | echohl None
    return
  endif

  " Debug output for filename
  echo "DEBUG: Final filename: '" . l:filename . "'"

  " Construct the full path to the topic file (keeping spaces)
  let l:topic_path = expand('%:p:h') . '/../../topics/' . l:filename . '.wiki'
  echo "DEBUG: Topic path: " . l:topic_path

  " For Vimwiki links, keep spaces if that's what you want
  let l:link = '../../topics/' . l:filename

  if filereadable(resolve(l:topic_path))
    " Replace the text with the link
    if l:was_visual
      " We had a visual selection - replace it
      execute "normal! gvc[[" . l:link . "|" . l:display . "]]"
    else
      " No visual selection - replace current word
      execute "normal! ciw[[" . l:link . "|" . l:display . "]]"
    endif
    echohl MoreMsg | echo "✅ Linked to topic: " . l:filename | echohl None

    " Get chapter tag from directory path
    let l:chapter_tag = ''
    let l:current_dir = expand('%:p:h:t')  " Get just the directory name
    echo "DEBUG: Current directory: " . l:current_dir
    
    " Check if directory matches pattern like 'ch8', 'ch10', etc.
    if l:current_dir =~# '^ch\d\+$'
      let l:chapter_num = substitute(l:current_dir, '^ch\(\d\+\)$', '\1', '')
      let l:chapter_tag = 'Ch. ' . l:chapter_num
      echo "DEBUG: Found chapter tag: " . l:chapter_tag
    endif

    " Update tags in the topic file only if we have a chapter tag
    if l:chapter_tag !=# ''
      let l:lines = readfile(l:topic_path)
      let l:found_tags = 0
      let l:changed = 0

      " Look for existing Tags line
      for i in range(len(l:lines))
        if l:lines[i] =~? '^Tags:'
          let l:found_tags = 1
          " Check if this chapter tag is already present
          if l:lines[i] !~ '\V' . l:chapter_tag
            let l:line = l:lines[i]
            " Remove trailing comma and whitespace if present
            let l:line = substitute(l:line, ',\s*$', '', '')
            " If only 'Tags:' present, don't prepend comma
            if l:line =~? '^Tags:\s*$'
              let l:lines[i] = 'Tags: ' . l:chapter_tag
            else
              let l:lines[i] = l:line . ', ' . l:chapter_tag
            endif
            let l:changed = 1
            echo "DEBUG: Updated existing Tags line"
          else
            echo "DEBUG: Chapter tag already present"
          endif
          break
        endif
      endfor

      " If no Tags line found, add one at the end
      if !l:found_tags
        call add(l:lines, 'Tags: ' . l:chapter_tag)
        let l:changed = 1
        echo "DEBUG: Added new Tags line"
      endif

      if l:changed
        call writefile(l:lines, l:topic_path)
        echohl MoreMsg | echo "📝 Updated Tags with: " . l:chapter_tag | echohl None
      endif
    else
      echo "DEBUG: No chapter tag found - not updating tags"
    endif
  else
    echohl WarningMsg | echo "⚠️ Topic not found: " . l:filename . ".wiki" | echohl None
  endif
endfunction

" Updated mappings - visual mode passes selected text as argument
function! GetVisualSelection()
  let l:save_reg = getreg('"')
  let l:save_regtype = getregtype('"')
  normal! gvy
  let l:selection = getreg('"')
  call setreg('"', l:save_reg, l:save_regtype)
  return l:selection
endfunction

xnoremap <leader>lt :<C-u>call LinkToTopic(GetVisualSelection())<CR>
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
