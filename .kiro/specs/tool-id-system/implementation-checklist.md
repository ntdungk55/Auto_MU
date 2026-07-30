# Tool ID System - Implementation Checklist

## ✅ CHECKLIST TỔNG QUAN

### Phase 1: Migration Script
- [ ] Tạo migration script `tools/migrate_to_uuid.py`
- [ ] Backup `tools/` → `tools_backup/`
- [ ] Backup `images/` → `images_backup/`
- [ ] Đọc tất cả tools cũ
- [ ] Generate UUID cho mỗi tool
- [ ] Update image_path trong actions (thay `{tool_name}` → `{tool_id}`)
- [ ] Lưu tools mới với tên `{uuid}.json`
- [ ] Move teaching images: `images/{tool_name}/` → `images/{uuid}/`
- [ ] Xóa files/folders cũ
- [ ] Verify migration thành công
- [ ] Test migration script với sample data

### Phase 2: Core Logic Changes
- [ ] Update Tool class
- [ ] Update ToolManager class
- [ ] Update image_path handling
- [ ] Add validation logic

### Phase 3: UI Changes
- [ ] Update MainWindow
- [ ] Update ToolEditorWindow
- [ ] Update ImageCaptureDialog
- [ ] Update action settings dialogs

### Phase 4: Testing
- [ ] Run unit tests
- [ ] Run manual tests
- [ ] Verify data persistence

---

## 📋 CHECKLIST CHI TIẾT

### 1. Tool Class (`src/logic/tool_manager.py`)

#### 1.1. Constructor
- [ ] Thêm parameter `id: Optional[str] = None`
- [ ] Auto-generate UUID nếu `id` is None: `self.id = id or str(uuid.uuid4())`
- [ ] Verify `self.id` có giá trị hợp lệ (36 chars)

#### 1.2. to_dict()
- [ ] Thêm `"id": self.id` vào dict
- [ ] Verify `"id"` xuất hiện đầu tiên trong dict (để dễ đọc)

#### 1.3. from_dict()
- [ ] Load `id` từ dict: `id=data.get("id")`
- [ ] Fallback: generate UUID nếu không có `id` (backward compatibility)
- [ ] Pass `id` vào Tool constructor

---

### 2. ToolManager Class (`src/logic/tool_manager.py`)

#### 2.1. save_tool()
- [ ] **CRITICAL**: Lưu file theo UUID: `filepath = os.path.join(self.tools_dir, f"{tool.id}.json")`
- [ ] **KHÔNG** lưu theo name nữa
- [ ] Verify file được tạo với tên UUID
- [ ] Test: Save tool → check file exists với tên `{uuid}.json`

#### 2.2. load_tool()
- [ ] Đổi signature: `def load_tool(self, tool_id: str) -> Optional[Tool]`
- [ ] Load file theo UUID: `filepath = os.path.join(self.tools_dir, f"{tool_id}.json")`
- [ ] **Fallback** (backward compatibility): Nếu không tìm thấy, thử load theo name
- [ ] Return Tool object hoặc None
- [ ] Test: Load tool by UUID → verify tool loaded correctly

#### 2.3. get_tool_by_name() - NEW
- [ ] Tạo method mới: `def get_tool_by_name(self, name: str) -> Optional[Tool]`
- [ ] Đọc tất cả tools trong `tools_dir`
- [ ] Tìm tool có `name` matching
- [ ] Return Tool object hoặc None
- [ ] Test: Find tool by name → verify correct tool returned

#### 2.4. list_tools()
- [ ] **CRITICAL**: Đổi return type: `List[Tuple[str, str]]` (id, name)
- [ ] Đọc tất cả files `.json` trong `tools_dir`
- [ ] Load mỗi file để lấy `id` và `name`
- [ ] Return list of `(id, name)` tuples
- [ ] Test: List tools → verify returns [(id, name), ...]

#### 2.5. delete_tool()
- [ ] Đổi signature: `def delete_tool(self, tool_id: str)`
- [ ] **CRITICAL**: Xóa file theo UUID: `filepath = os.path.join(self.tools_dir, f"{tool_id}.json")`
- [ ] **CRITICAL**: Xóa teaching images folder: `images/{tool_id}/`
- [ ] Test: Delete tool → verify file and images deleted

#### 2.6. validate_unique_name() - NEW
- [ ] Tạo method mới: `def validate_unique_name(self, name: str, exclude_id: Optional[str] = None) -> bool`
- [ ] Đọc tất cả tools
- [ ] Check nếu có tool nào có cùng `name` (và khác `exclude_id`)
- [ ] Return True nếu unique, False nếu duplicate
- [ ] Test: Validate unique name → verify rejects duplicates

---

### 3. Teaching Images Path (`src/ui/image_capture_dialog.py`)

#### 3.1. Constructor
- [ ] **CRITICAL**: Đổi parameter: `tool_id: Optional[str] = None` (thay vì `tool_name`)
- [ ] Store `self.tool_id = tool_id`
- [ ] Remove `self.tool_name` (không cần nữa)

#### 3.2. get_cropped_image_path()
- [ ] **CRITICAL**: Lưu ảnh vào `images/{tool_id}/` thay vì `images/{tool_name}/`
- [ ] Code: `images_dir = os.path.join("images", self.tool_id) if self.tool_id else "images"`
- [ ] Verify path format: `images/{uuid}/capture_*.png`
- [ ] Test: Capture image → verify saved to `images/{uuid}/`

#### 3.3. _sanitize_tool_folder_name() - DEPRECATED
- [ ] Method này không cần nữa (vì dùng UUID, không cần sanitize)
- [ ] Có thể giữ lại để backward compatibility
- [ ] Hoặc xóa và update tất cả references

---

### 4. MainWindow (`main.py`)

#### 4.1. tool_combo
- [ ] **CRITICAL**: Lưu tool ID trong `itemData`: `self.tool_combo.addItem(tool_name, userData=tool_id)`
- [ ] Hiển thị tool name (không đổi UI)
- [ ] Test: Select tool → verify correct tool ID retrieved

#### 4.2. refresh_tools()
- [ ] Call `self.tool_manager.list_tools()` → returns `[(id, name), ...]`
- [ ] Loop qua list và add items: `self.tool_combo.addItem(name, userData=id)`
- [ ] Test: Refresh tools → verify combo populated correctly

#### 4.3. edit_tool()
- [ ] Get tool ID: `tool_id = self.tool_combo.itemData(current_index)`
- [ ] **CRITICAL**: Pass tool ID to ToolEditorWindow: `ToolEditorWindow(tool_id=tool_id, ...)`
- [ ] Test: Edit tool → verify correct tool loaded

#### 4.4. delete_tool()
- [ ] Get tool ID: `tool_id = self.tool_combo.itemData(current_index)`
- [ ] **CRITICAL**: Delete by ID: `self.tool_manager.delete_tool(tool_id)`
- [ ] Test: Delete tool → verify tool and images deleted

#### 4.5. _save_selected_tool_settings()
- [ ] Get tool ID: `tool_id = self.tool_combo.itemData(current_index)`
- [ ] **CRITICAL**: Load tool by ID: `tool = self.tool_manager.load_tool(tool_id)`
- [ ] Update settings
- [ ] Save tool: `self.tool_manager.save_tool(tool)`
- [ ] Test: Save settings → verify settings persisted

#### 4.6. _on_tool_combo_changed()
- [ ] Get tool ID: `tool_id = self.tool_combo.itemData(index)`
- [ ] Save tool ID to app state (thay vì tool name)
- [ ] Test: Change tool → verify correct tool ID saved

#### 4.7. _restore_last_selected_tool()
- [ ] Load tool ID from app state
- [ ] Find combo index by tool ID (not name)
- [ ] Set current index
- [ ] Test: Restore last tool → verify correct tool selected

---

### 5. ToolEditorWindow (`src/ui/tool_editor_window.py`)

#### 5.1. Constructor
- [ ] **CRITICAL**: Đổi parameter: `tool_id: Optional[str] = None` (thay vì `tool_name`)
- [ ] Store `self.tool_id = tool_id`
- [ ] Store `self.tool_name = None` (will be loaded)
- [ ] Update window title logic

#### 5.2. load_tool()
- [ ] **CRITICAL**: Load by ID: `tool = self.tool_manager.load_tool(self.tool_id)`
- [ ] Store `self.tool_name = tool.name`
- [ ] Load actions
- [ ] Test: Load tool → verify correct tool loaded

#### 5.3. save_tool()
- [ ] Get name from input: `name = self.name_input.text().strip()`
- [ ] **CRITICAL**: Validate unique name: `self.tool_manager.validate_unique_name(name, exclude_id=self.tool_id)`
- [ ] If duplicate → show error, return
- [ ] If editing existing tool:
  - [ ] Load tool by ID
  - [ ] Update `tool.name = name`
  - [ ] Update `tool.actions = self.actions`
  - [ ] Save tool (same ID)
- [ ] If creating new tool:
  - [ ] Create new Tool (auto-generate ID)
  - [ ] Store `self.tool_id = tool.id`
  - [ ] Save tool
- [ ] Test: Save tool → verify saved with correct ID
- [ ] Test: Rename tool → verify ID unchanged, name updated

#### 5.4. add_action() / edit_action()
- [ ] **CRITICAL**: Pass tool ID to ActionConfigDialog: `ActionConfigDialog(..., tool_id=self.tool_id)`
- [ ] Test: Add/edit action → verify teaching images use tool ID

---

### 6. ActionConfigDialog (`src/ui/action_config_dialog.py`)

#### 6.1. Constructor
- [ ] **CRITICAL**: Đổi parameter: `tool_id: Optional[str] = None` (thay vì `tool_name`)
- [ ] Store `self.tool_id = tool_id`
- [ ] Pass tool ID to child dialogs

#### 6.2. Child Dialogs
- [ ] Pass tool ID to ImageDetectSettingsDialog
- [ ] Pass tool ID to MouseClickSettingsDialog
- [ ] Pass tool ID to PassiveReadSettingsDialog
- [ ] Test: Open dialogs → verify tool ID passed correctly

---

### 7. Action Settings Dialogs

#### 7.1. ImageDetectSettingsDialog (`src/ui/image_detect_settings_dialog.py`)
- [ ] Constructor: Accept `tool_id` parameter
- [ ] Pass tool ID to ImageCaptureDialog
- [ ] Test: Capture teaching image → verify saved to `images/{tool_id}/`

#### 7.2. MouseClickSettingsDialog (`src/ui/mouse_click_settings_dialog.py`)
- [ ] Constructor: Accept `tool_id` parameter
- [ ] Pass tool ID to ImageCaptureDialog
- [ ] Test: Capture teaching image → verify saved to `images/{tool_id}/`

#### 7.3. PassiveReadSettingsDialog (`src/ui/passive_read_settings_dialog.py`)
- [ ] Constructor: Accept `tool_id` parameter
- [ ] Pass tool ID to ImageCaptureDialog
- [ ] Test: Capture teaching image → verify saved to `images/{tool_id}/`

---

### 8. Migration Script (`tools/migrate_to_uuid.py`)

#### 8.1. Backup Function
- [ ] Create `backup_folders()` function
- [ ] Copy `tools/` → `tools_backup/`
- [ ] Copy `images/` → `images_backup/`
- [ ] Verify backup successful
- [ ] Test: Run backup → verify folders copied

#### 8.2. Migrate Tools Function
- [ ] Create `migrate_tools()` function
- [ ] List all `.json` files in `tools/`
- [ ] For each tool:
  - [ ] Load JSON
  - [ ] Generate UUID
  - [ ] Add `"id"` field to JSON
  - [ ] Update `image_path` in actions (replace `{tool_name}` → `{tool_id}`)
  - [ ] Save to `tools/{uuid}.json`
  - [ ] Delete old file `tools/{tool_name}.json`
- [ ] Test: Migrate tools → verify all tools have UUID

#### 8.3. Migrate Images Function
- [ ] Create `migrate_images()` function
- [ ] For each tool (with UUID):
  - [ ] Find old images folder: `images/{tool_name}/`
  - [ ] Move to new folder: `images/{tool_id}/`
  - [ ] Verify files moved successfully
  - [ ] Delete old folder
- [ ] Test: Migrate images → verify folders renamed

#### 8.4. Validation Function
- [ ] Create `validate_migration()` function
- [ ] Check all tools have `"id"` field
- [ ] Check all tool IDs are unique
- [ ] Check all tool names are unique
- [ ] Check all image_path in actions exist
- [ ] Check no old files/folders remain
- [ ] Test: Validate → verify migration complete

#### 8.5. Main Function
- [ ] Call backup_folders()
- [ ] Call migrate_tools()
- [ ] Call migrate_images()
- [ ] Call validate_migration()
- [ ] Print summary report
- [ ] Test: Run full migration → verify success

---

### 9. Data Persistence Verification

#### 9.1. Tool Settings
- [ ] Create tool with settings (loop, timeout, etc.)
- [ ] Save tool
- [ ] Close app
- [ ] Reopen app
- [ ] Load tool by ID
- [ ] **VERIFY**: All settings persisted correctly

#### 9.2. Teaching Images
- [ ] Create tool
- [ ] Add action with teaching image
- [ ] Save tool
- [ ] **VERIFY**: Image saved to `images/{tool_id}/`
- [ ] Close app
- [ ] Reopen app
- [ ] Load tool
- [ ] **VERIFY**: Image path correct and image loads

#### 9.3. Rename Tool
- [ ] Create tool "Tool A" with teaching images
- [ ] Note tool ID
- [ ] Rename to "Tool B"
- [ ] **VERIFY**: Tool ID unchanged
- [ ] **VERIFY**: Teaching images path unchanged (`images/{tool_id}/`)
- [ ] **VERIFY**: Images still load correctly

#### 9.4. Multiple Tools
- [ ] Create 3 tools with teaching images
- [ ] **VERIFY**: Each tool has unique UUID
- [ ] **VERIFY**: Each tool has separate images folder
- [ ] **VERIFY**: No cross-contamination of images

---

### 10. Unit Tests

#### 10.1. Tool Class Tests
- [ ] `test_tool_has_id_field()` - PASS
- [ ] `test_tool_generates_uuid_if_not_provided()` - PASS
- [ ] `test_tool_accepts_custom_id()` - PASS
- [ ] `test_tool_to_dict_includes_id()` - PASS
- [ ] `test_tool_from_dict_loads_id()` - PASS

#### 10.2. ToolManager Tests
- [ ] `test_tool_manager_saves_by_id()` - PASS
- [ ] `test_tool_manager_loads_by_id()` - PASS
- [ ] `test_tool_manager_get_tool_by_name()` - PASS
- [ ] `test_tool_manager_list_tools_returns_id_and_name()` - PASS
- [ ] `test_tool_manager_delete_by_id()` - PASS
- [ ] `test_tool_manager_validate_unique_name_allows_same_tool()` - PASS
- [ ] `test_tool_manager_validate_unique_name_rejects_duplicate()` - PASS
- [ ] `test_tool_manager_validate_unique_name_allows_new_name()` - PASS

#### 10.3. Rename Tests
- [ ] `test_rename_tool_updates_name_only()` - PASS
- [ ] `test_teaching_image_path_uses_tool_id()` - PASS
- [ ] `test_action_image_path_updated_after_rename()` - PASS

#### 10.4. Migration Tests
- [ ] `test_migration_preserves_all_tool_data()` - PASS

#### 10.5. Edge Cases
- [ ] `test_empty_tools_directory()` - PASS
- [ ] `test_load_nonexistent_tool()` - PASS
- [ ] `test_get_tool_by_name_nonexistent()` - PASS

---

### 11. Manual Tests

- [ ] Test Case 1: Migration Script - PASS
- [ ] Test Case 2: Load Tools Sau Migration - PASS
- [ ] Test Case 3: Rename Tool - PASS
- [ ] Test Case 4: Rename Tool - Trùng Tên - PASS
- [ ] Test Case 5: Create New Tool - PASS
- [ ] Test Case 6: Delete Tool - PASS
- [ ] Test Case 7: Teaching Images Path - PASS
- [ ] Test Case 8: Rename Tool - Teaching Images Không Đổi - PASS
- [ ] Test Case 9: Run Tool Sau Migration - PASS
- [ ] Test Case 10: Tool Settings Persist - PASS
- [ ] Test Case 11: Multiple Tools - No Conflict - PASS
- [ ] Test Case 12: Rollback Migration - PASS

---

## 🎯 CRITICAL CHECKPOINTS

### Before Migration
- [ ] Backup đã được tạo
- [ ] Migration script đã được test với sample data
- [ ] User đã được thông báo về migration

### After Migration
- [ ] Tất cả tools có UUID
- [ ] Tất cả teaching images trong folders UUID
- [ ] Không còn files/folders cũ
- [ ] App load được tất cả tools

### Before Commit
- [ ] Tất cả unit tests PASS
- [ ] Tất cả manual tests PASS
- [ ] Teaching images load đúng
- [ ] Tool settings persist đúng
- [ ] Rename tool hoạt động đúng

---

## 📊 PROGRESS TRACKING

**Phase 1: Migration Script**
- Status: ⏳ Not Started
- Files: 1 new file

**Phase 2: Core Logic**
- Status: ⏳ Not Started
- Files: 1 modified file

**Phase 3: UI Changes**
- Status: ⏳ Not Started
- Files: 7 modified files

**Phase 4: Testing**
- Status: ⏳ Not Started
- Tests: 25 unit tests + 12 manual tests

**Total Progress: 0%**

---

## ✅ FINAL VERIFICATION

Trước khi hoàn thành feature, verify:

- [ ] ✅ Tất cả tools có UUID unique
- [ ] ✅ Teaching images lưu theo UUID: `images/{uuid}/`
- [ ] ✅ Tool settings lưu theo UUID: `tools/{uuid}.json`
- [ ] ✅ Rename tool không tạo duplicate
- [ ] ✅ Rename tool không ảnh hưởng teaching images
- [ ] ✅ Không cho phép trùng tên tool
- [ ] ✅ Migration script chạy thành công
- [ ] ✅ Tất cả unit tests PASS
- [ ] ✅ Tất cả manual tests PASS
- [ ] ✅ Có thể rollback nếu cần

**Nếu tất cả ✅ → Feature hoàn thành!**
