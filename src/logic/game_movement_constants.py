"""Constants for MU character movement click calibration."""

GAME_CLIENT_WIDTH = 784
GAME_CLIENT_HEIGHT = 557
GAME_CLIENT_CENTER_X = 392
GAME_CLIENT_CENTER_Y = 278

# Clicking inside this rectangle does not move the character.
MOVEMENT_DEAD_ZONE_X_MIN = 348
MOVEMENT_DEAD_ZONE_X_MAX = 438
MOVEMENT_DEAD_ZONE_Y_MIN = 237
MOVEMENT_DEAD_ZONE_Y_MAX = 290

# Safe click points measured from the current client coordinate system.
MOVE_CLICK_LEFT = (342, 278)
MOVE_CLICK_RIGHT = (444, 278)
MOVE_CLICK_UP = (392, 232)
MOVE_CLICK_DOWN = (392, 296)
MOVE_CLICK_UP_LEFT = (342, 232)
MOVE_CLICK_UP_RIGHT = (444, 232)
MOVE_CLICK_DOWN_LEFT = (342, 296)
MOVE_CLICK_DOWN_RIGHT = (444, 296)

# Map coordinate axes are rotated 45 degrees relative to screen/client clicks:
# - Map +X: screen down-right
# - Map -X: screen up-left
# - Map +Y: screen up-right
# - Map -Y: screen down-left
MAP_MOVE_POSITIVE_X = MOVE_CLICK_DOWN_RIGHT
MAP_MOVE_NEGATIVE_X = MOVE_CLICK_UP_LEFT
MAP_MOVE_POSITIVE_Y = MOVE_CLICK_UP_RIGHT
MAP_MOVE_NEGATIVE_Y = MOVE_CLICK_DOWN_LEFT

# Recommended step distances from the character center.
MOVEMENT_HORIZONTAL_STEP = 55
MOVEMENT_VERTICAL_UP_STEP = 50
MOVEMENT_VERTICAL_DOWN_STEP = 25

# 500ms can still lose steps; 700ms is the current safe click interval.
MOVEMENT_STEP_INTERVAL_MS = 700
