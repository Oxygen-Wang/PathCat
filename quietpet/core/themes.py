"""QuietPet application palettes; no changes to Windows global colors."""
KEYS = ('BG', 'FG', 'MUTED', 'BTN', 'BTN_HOVER', 'SEL', 'SEL_FG', 'DROP_BG')
PALETTES = {
    'dark': ('#1e1f22', '#e4e6e9', '#a1a5ad', '#2a2c31', '#3a3d43', '#304c69', '#ffffff', '#385a48'),
    'light': ('#ffffff', '#25282c', '#626870', '#f0f2f4', '#e1e5e9', '#d9e5f0', '#172d42', '#d8eadc'),
    'cream': ('#f4eedf', '#38342b', '#6d6556', '#e9e1cf', '#ded3bb', '#d6c7a5', '#30291b', '#d7dfc5'),
    'sage': ('#e8eee4', '#2d392d', '#586653', '#dce5d5', '#cbd8c3', '#bdd1b3', '#253b22', '#bcd3be'),
    'slate': ('#e7edf1', '#293741', '#556671', '#d8e2e9', '#c6d5df', '#b5cbd9', '#203749', '#c6dccf'),
}


def palette(name):
    return dict(zip(KEYS, PALETTES[name if name in PALETTES else 'dark']))


def initialize_settings(settings):
    # One-time migration makes the user's requested shortcut apply to existing installs.
    if not settings.get('hotkey_ctrl_b_migrated'):
        settings['hotkey'] = 'Ctrl+B'
        settings['hotkey_ctrl_b_migrated'] = True
    return settings
