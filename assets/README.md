# Custom Assets

Put your own assets here to replace the built-in placeholders and procedural fallbacks.

## Images

Place files in `assets/images/`:

- `menu_background.png` or `menu_background.jpg` - main menu background
- `settings_background.png` or `settings_background.jpg` - settings screen background
- `forest_background.png` or `forest_background.jpg` - level 1 forest background
- `forest_layer_1.png` ... `forest_layer_12.png` - parallax layers for level 1, from far back to front
  If any of them are missing, the game can fall back to `forest_layer_1_auto.png` ... `forest_layer_12_auto.png` where available.
- `player_idle.png` or `dipper_idle.png` - player idle sprite
- `player_run_1.png` or `dipper_run_1.png` - first running frame
- `player_run_2.png` or `dipper_run_2.png` - second running frame
- `player_run_3.png` or `dipper_run_3.png` - third running frame
- `player_run_4.png` or `dipper_run_4.png` - fourth running frame
- `gnome_idle.png` - idle frame for the level 1 gnome enemy
- `gnome_run_1.png` ... `gnome_run_4.png` - running animation frames for the level 1 gnome enemy
- `bunker_background.png` or `bunker_background.jpg` - level 2 bunker background
- `boss_background.png` or `boss_background.jpg` - level 3 boss arena background
- `settings_panel.png` - large central panel for the settings screen
- `settings_row.png` - default row/button for settings options
- `settings_row_active.png` - highlighted row/button for active settings
- `settings_slider_bar.png` - slider background bar
- `settings_slider_fill.png` - filled slider segment
- `settings_slider_knob.png` - slider knob/handle
- `settings_arrow_left.png` - left difficulty arrow
- `settings_arrow_right.png` - right difficulty arrow
- `settings_difficulty.png` - central difficulty label plate
- `fullscreen_button_idle.png` - fullscreen toggle button, idle state
- `fullscreen_button_hover.png` - fullscreen toggle button, hover state
- `music_toggle_on.png` or `music_on_idle.png` - music ON button, idle state
- `music_toggle_on_hover.png` or `music_on_hover.png` - music ON button, hover state
- `music_toggle_off.png` or `music_off_idle.png` - music OFF button, idle state
- `music_toggle_off_hover.png` or `music_off_hover.png` - music OFF button, hover state
- `button.png` or `button_idle.png` - default button look
- `button_hover.png` or `button_active.png` - button look on hover

## Fonts

Place files in `assets/fonts/`:

- `title.ttf` - large title font
- `ui.ttf` - main UI font for buttons and labels
- `mono.ttf` - small helper text font

## Audio

Place files in `assets/audio/`:

- `menu_music.ogg`, `menu_music.mp3`, or `menu_music.wav`
- or `bg_music.ogg`, `bg_music.mp3`, or `bg_music.wav`

If these files are missing, the game will keep using the built-in fallback visuals and generated music.
