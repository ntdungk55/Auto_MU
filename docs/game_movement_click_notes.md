# Game Movement Click Notes

Window: `MU GamethuVN - Season 21 (Golden - EmXinhVui)`

Runtime constants:
- `src/logic/game_movement_constants.py`

Measured client/game area:
- Client size: `784x557`
- Client center: `(392, 278)`

Dead zone where clicking does not move the character:
- Horizontal: `x = 348..438`
- Vertical: `y = 237..290`

Safe movement click points from center:
- Left: `(342, 278)`
- Right: `(444, 278)`
- Up: `(392, 232)`
- Down: `(392, 296)`
- Up-left: `(342, 232)`
- Up-right: `(444, 232)`
- Down-left: `(342, 296)`
- Down-right: `(444, 296)`

Map coordinate system is rotated 45 degrees relative to screen/client clicks:
- Map `+X`: click screen down-right `(444, 296)`
- Map `-X`: click screen up-left `(342, 232)`
- Map `+Y`: click screen up-right `(444, 232)`
- Map `-Y`: click screen down-left `(342, 296)`

Minimum distance from center to leave dead zone:
- Left: `45px`
- Right: `47px`
- Up: `42px`
- Down: `13px`

Recommended step values:
- `horizontal_step = 55`
- `vertical_up_step = 50`
- `vertical_down_step = 25`
- `movement_step_interval_ms = 700`

Manual click command:
```powershell
python click_game.py 392 296
```

Repeat click command:
```powershell
python click_game.py 392 296 5 700
```

Map path command:
```powershell
python click_game.py path 222 45 222 29 237 27
```

Arguments:
- `x y`: client/game coordinate.
- `repeat`: number of clicks, default `1`.
- `interval_ms`: delay between clicks in milliseconds, default `MOVEMENT_STEP_INTERVAL_MS = 700`.

Observed timing:
- `500ms` can still lose steps.
- `700ms` is the current recommended safe interval between movement clicks.
