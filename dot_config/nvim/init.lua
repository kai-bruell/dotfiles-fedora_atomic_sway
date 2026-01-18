-- Zeilennummern
vim.opt.relativenumber = true  -- Relative Zeilennummern
vim.opt.number = true          -- Absolute Nummer auf aktueller Zeile

-- Schwarzer Hintergrund
vim.opt.background = 'dark'
vim.cmd('highlight Normal guibg=#000000 ctermbg=0')
vim.cmd('highlight NonText guibg=#000000 ctermbg=0')
vim.cmd('highlight NormalNC guibg=#000000 ctermbg=0')

-- Graue Statusleiste
vim.cmd('highlight StatusLine guibg=#3a3a3a guifg=#ffffff ctermbg=237 ctermfg=15')
vim.cmd('highlight StatusLineNC guibg=#2a2a2a guifg=#808080 ctermbg=235 ctermfg=244')
