# Feature: Tool ID System - UUID-based Tool Management

## 1. Tổng quan

Hiện tại tools được lưu theo tên file (`tools/{tool_name}.json`), dẫn đến vấn đề khi user đổi tên tool sẽ tạo ra tool mới (duplicate) thay vì rename. Feature này thay đổi cách quản lý tools bằng UUID, cho phép rename tool mà không tạo duplicate.

## 2. User Stories

- Là user, tôi muốn đổi tên tool mà không tạo ra tool mới, để quản lý tools dễ dàng hơn
- Là user, tôi muốn tools được quản lý bằng ID duy nhất, để tránh conflict khi có nhiều tools
- Là developer, tôi muốn teaching images được lưu theo tool ID, để dễ dàng quản lý và cleanup
- Là user, tôi muốn migrate tất cả tools hiện tại sang format mới, để đảm bảo tính nhất quán

## 3. Acceptance Criteria

1. ✅ Tool class có field `id: str` (UUID)
2. ✅ Tools được lưu theo UUID: `tools/{uuid}.json`
3. ✅ Teaching images được lưu theo UUID: `images/{uuid}/`
4. ✅ UI vẫn hiển thị tool name (không thay đổi giao diện)
5. ✅ Cho phép rename tool mà không tạo duplicate
6. ✅ Không cho phép 2 tools có cùng tên
7. ✅ Migration script tự động migrate tất cả tools hiện tại
8. ✅ Backup tự động trước khi migrate
9. ✅ Sau migration, code chỉ hỗ trợ tools có UUID

## 4. Input/Output

**Input:**
- Tools hiện tại: `tools/{tool_name}.json` (tên được sanitize)
- Teaching images: `images/{tool_name}/capture_*.png`
- User action: Đổi tên tool trong UI

**Output:**
- Tools mới: `tools/{uuid}.json`
- Teaching images: `images/{uuid}/capture_*.png`
- Backup: `tools_backup/`, `images_backup/`
- Tool có thể rename mà không tạo duplicate

## 5. Sơ đồ khối

```
┌─────────────────────────────────────────────────────────────┐
│                    MIGRATION SCRIPT                         │
│  (Chạy trước khi sửa code)                                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Backup                                                  │
│     - tools/ → tools_backup/                                │
│     - images/ → images_backup/                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Migrate Tools                                           │
│     - Đọc tất cả tools cũ                                   │
│     - Generate UUID cho mỗi tool                            │
│     - Thêm field "id" vào JSON                              │
│     - Lưu lại: tools/{uuid}.json                            │
│     - Update image_path trong actions                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  3. Migrate Teaching Images                                 │
│     - Move: images/{tool_name}/ → images/{uuid}/            │
│     - Verify files đã move thành công                       │
│     - Xóa folder cũ                                         │
└─────────────────────────────────────────────────────────────┐
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  4. Cleanup                                                 │
│     - Xóa tools/{tool_name}.json cũ                         │
│     - Verify migration thành công                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    CODE CHANGES                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Tool Class                                                 │
│  - Thêm field: id (UUID)                                    │
│  - Constructor: Generate UUID nếu không có                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ToolManager                                                │
│  - save_tool(): Lưu theo {id}.json                          │
│  - load_tool(id): Load theo ID                              │
│  - get_tool_by_name(name): Tìm tool theo tên               │
│  - list_tools(): Trả về [(id, name), ...]                  │
│  - delete_tool(id): Xóa theo ID                             │
│  - validate_unique_name(name, exclude_id): Check trùng tên  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  MainWindow                                                 │
│  - tool_combo: Hiển thị name, lưu ID trong itemData        │
│  - refresh_tools(): Load và map ID → name                  │
│  - edit_tool(): Pass tool ID                                │
│  - delete_tool(): Xóa theo ID                               │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ToolEditorWindow                                           │
│  - Constructor: Nhận tool_id thay vì tool_name              │
│  - save_tool(): Validate trùng tên, lưu theo ID             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  ImageCaptureDialog                                         │
│  - Lưu teaching images vào: images/{tool_id}/               │
└─────────────────────────────────────────────────────────────┘
```

## 6. Technical Notes

### Migration Strategy

**Thứ tự thực hiện:**
1. Chạy migration script TRƯỚC khi sửa code
2. Migration script tự động backup
3. Sau migration, test thủ công
4. Nếu OK, commit code changes
5. Nếu lỗi, user có thể revert bằng git

**Migration Script Logic:**
```python
import uuid
import json
import os
import shutil

def migrate_tools():
    # 1. Backup
    backup_folders()
    
    # 2. Migrate tools
    tools_dir = "tools"
    for filename in os.listdir(tools_dir):
        if not filename.endswith('.json'):
            continue
        
        # Load old tool
        old_path = os.path.join(tools_dir, filename)
        with open(old_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Generate UUID
        tool_id = str(uuid.uuid4())
        data['id'] = tool_id
        
        # Update image paths in actions
        old_tool_name = data['name']
        old_folder = sanitize_name(old_tool_name)
        new_folder = tool_id
        
        for action in data.get('actions', []):
            if 'image_path' in action and action['image_path']:
                old_path = action['image_path']
                if f'images/{old_folder}/' in old_path:
                    action['image_path'] = old_path.replace(
                        f'images/{old_folder}/',
                        f'images/{new_folder}/'
                    )
        
        # Save new tool
        new_path = os.path.join(tools_dir, f"{tool_id}.json")
        with open(new_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # Move teaching images
        old_images_dir = os.path.join("images", old_folder)
        new_images_dir = os.path.join("images", new_folder)
        if os.path.exists(old_images_dir):
            shutil.move(old_images_dir, new_images_dir)
        
        # Delete old tool file
        os.remove(old_path)
```

### Validation Rules

**Tool name uniqueness:**
- Khi save tool, check tất cả tools khác
- Nếu tìm thấy tool khác có cùng tên (và khác ID) → reject
- Error message: "Tên tool đã tồn tại. Vui lòng chọn tên khác."

**UUID format:**
- Sử dụng `uuid.uuid4()` để generate
- Format: `xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx`
- Example: `550e8400-e29b-41d4-a716-446655440000`

### Backward Compatibility

**Sau migration:**
- Code chỉ hỗ trợ tools có field `id`
- Nếu load tool không có `id` → raise error
- User phải chạy migration script trước

### Data Integrity

**Checks cần thực hiện:**
1. Tất cả tools phải có field `id`
2. Tất cả `id` phải unique
3. Tất cả tool names phải unique
4. Teaching images paths phải tồn tại
5. Image paths trong actions phải match với folder structure

### Error Handling

**Migration errors:**
- Backup failed → abort migration
- Tool load failed → skip tool, log error
- Image move failed → rollback, restore backup
- Validation failed → abort migration

**Runtime errors:**
- Tool không có ID → raise ValueError
- Trùng tên tool → show error dialog
- Teaching image không tồn tại → warning (không crash)

## 7. Files Affected

### Major Changes
- `src/logic/tool_manager.py` (~200 lines changed)
- `main.py` (~100 lines changed)
- `src/ui/tool_editor_window.py` (~50 lines changed)
- `src/ui/image_capture_dialog.py` (~30 lines changed)

### Minor Changes
- `src/ui/action_config_dialog.py` (~10 lines)
- `src/ui/passive_read_settings_dialog.py` (~10 lines)
- `src/ui/image_detect_settings_dialog.py` (~10 lines)
- `src/ui/mouse_click_settings_dialog.py` (~10 lines)

### New Files
- `tools/migrate_to_uuid.py` (migration script)
- `tests/test_tool_id_system.py` (unit tests)
- `docs/MANUAL_TEST_TOOL_ID_SYSTEM.md` (manual test plan)

## 8. Testing Strategy

### Unit Tests
- Test Tool class với UUID
- Test ToolManager save/load theo ID
- Test validation trùng tên
- Test migration script logic

### Manual Tests
- Test rename tool
- Test create new tool
- Test delete tool
- Test teaching images paths
- Test migration script end-to-end

## 9. Rollback Plan

**Nếu migration lỗi:**
1. Stop app
2. Delete `tools/` và `images/`
3. Restore từ `tools_backup/` và `images_backup/`
4. Restart app với code cũ (git revert)

**Nếu code lỗi sau migration:**
1. Git revert code changes
2. Chạy migration script ngược (restore từ backup)
3. Fix bugs
4. Re-run migration

## 10. Performance Impact

**Migration:**
- Thời gian: ~1-2 giây cho 10 tools
- Disk space: Backup chiếm 2x dung lượng hiện tại (tạm thời)

**Runtime:**
- Load tool: Không thay đổi (vẫn đọc JSON)
- Save tool: Không thay đổi
- List tools: Thêm 1 lần đọc JSON để lấy name (negligible)

## 11. Security Considerations

**UUID collision:**
- Xác suất collision của UUID v4: ~10^-37 (negligible)
- Không cần check duplicate UUID

**File permissions:**
- Migration script cần quyền write vào `tools/` và `images/`
- Backup folders cần quyền write

## 12. Future Enhancements

**Possible improvements:**
- Tool versioning (track changes history)
- Tool export/import (share tools between users)
- Tool templates (create tool from template)
- Tool categories/tags (organize tools)
