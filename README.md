# dotfiles

Chezmoi-managed dotfiles for Fedora Atomic Sway.

## Setup

```bash
chezmoi init --apply git@github.com:kai-bruell/dotfiles-fedora_atomic_sway.git
```

## Usage

```bash
chezmoi update    # pull and apply changes
chezmoi diff      # preview changes
chezmoi apply     # apply changes
chezmoi cd        # navigate to source repo
```

## Structure

```
dot_config/
└── sway/           # Sway window manager config
    ├── config
    ├── config.d/
    └── run_after_reload.sh
```

## Machine-specific config

See `docs/chezmoi.toml.example` for available options.
