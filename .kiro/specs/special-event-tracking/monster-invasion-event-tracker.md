# Monster Invasion Event Tracker - Requirements

## 1. SPEC (Dac ta)

**Van de:**
Co nhieu su kien boss xuat hien trong game MU Online dung chung co che doc thong bao tieu diet. Moi su kien co lich gio va logic rieng nhung deu can doc cung 1 vung channel va 1 vung thong bao. Neu moi su kien co ROI/OCR rieng se gay trung lap cau hinh va ton tai nguyen.

**Muc tieu:**
Gop cac su kien boss invasion vao 1 event cha Monster Invasion voi 2 vung OCR dung chung (channel + thong bao). Moi sub-event bat/tat doc lap va xu ly logic rieng, nhung nhan OCR text tu cung 1 subscription.

**Danh sach sub-events:**

| Sub-event                  | File Requirements                                                                                    | Trang thai |
|----------------------------|------------------------------------------------------------------------------------------------------|------------|
| Golden Invasion            | `.kiro/specs/special-event-tracking/golden-invasion-event-tracker.md`                               | Active     |
| White Wizard + Red Dragon  | `.kiro/specs/special-event-tracking/white-wizard-red-dragon-event-tracker.md`                       | Active     |

**Input/Output (framework):**

| Loai   | Mo ta                                                                 | Vi du                                                                |
|--------|-----------------------------------------------------------------------|----------------------------------------------------------------------|
| Input  | OCR text tu Vung 1 (channel)                                         | "CS1"                                                                |
| Input  | OCR text tu Vung 2 (thong bao)                                       | "Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia"           |
| Output | Fan-out text den cac sub-handler dang enabled                        | GoldenInvasionSubHandler + WhiteWizardRedDragonSubHandler            |

**Parameters (framework - dung chung cho tat ca sub-events):**

| Tham so                                          | Kieu    | Mo ta                                                              | Gia tri mac dinh |
|--------------------------------------------------|---------|--------------------------------------------------------------------|------------------|
| `monster_invasion_enabled`                       | bool    | Bat/tat toan bo Monster Invasion event                             | false            |
| `monster_invasion_channel_roi_x1`                | int     | Vung 1 (channel) - toa do x1                                      | 0                |
| `monster_invasion_channel_roi_y1`                | int     | Vung 1 (channel) - toa do y1                                      | 0                |
| `monster_invasion_channel_roi_x2`                | int     | Vung 1 (channel) - toa do x2                                      | 0                |
| `monster_invasion_channel_roi_y2`                | int     | Vung 1 (channel) - toa do y2                                      | 0                |
| `monster_invasion_channel_ocr_engine`            | str     | OCR engine cho Vung 1                                              | "auto"           |
| `monster_invasion_channel_ocr_algorithms`        | list    | Preprocessing algorithms cho Vung 1                               | []               |
| `monster_invasion_channel_teaching_image_path`   | str     | Teaching image path cho Vung 1                                     | ""               |
| `monster_invasion_notify_roi_x1`                 | int     | Vung 2 (thong bao) - toa do x1                                    | 0                |
| `monster_invasion_notify_roi_y1`                 | int     | Vung 2 (thong bao) - toa do y1                                    | 0                |
| `monster_invasion_notify_roi_x2`                 | int     | Vung 2 (thong bao) - toa do x2                                    | 0                |
| `monster_invasion_notify_roi_y2`                 | int     | Vung 2 (thong bao) - toa do y2                                    | 0                |
| `monster_invasion_notify_ocr_engine`             | str     | OCR engine cho Vung 2                                              | "auto"           |
| `monster_invasion_notify_ocr_algorithms`         | list    | Preprocessing algorithms cho Vung 2                               | []               |
| `monster_invasion_notify_teaching_image_path`    | str     | Teaching image path cho Vung 2                                     | ""               |
| `monster_invasion_match_threshold`               | float   | Nguong fuzzy matching dung chung cho tat ca sub-events (0-100)    | 70.0             |

> Cac tham so rieng cua tung sub-event (lich gio, server time, v.v.) duoc dinh nghia trong file requirements cua sub-event do.

---

## 2. SO DO HOAT DONG

```
+------------------------------------------------------------------+
|  Monster Invasion duoc kich hoat                                 |
|  (mode special_event_tracking, monster_invasion_enabled = true)  |
+------------------------------------------------------------------+
               |
               v
+------------------------------------------------------------------+
|  Kiem tra ROI hop le?                                            |
+------------------------------------------------------------------+
       |                    |
    Khong                  Co
       v                    v
+----------+    +------------------------------------------+
| Canh bao |    | Tao 2 OCRSubscription dung chung:        |
| khong    |    | - Vung 1: mi:channel callback            |
| subscribe|    | - Vung 2: mi:notify callback             |
+----------+    | Khoi tao sub-handlers dang enabled       |
                +------------------------------------------+
                               |
                               | OCR callback
                               v
                +------------------------------------------+
                |  MonsterInvasionHandler nhan text        |
                |  Fan-out den cac sub-handler enabled:    |
                |                                          |
                |  on_channel_text(text):                  |
                |    -> GoldenInvasionSubHandler           |
                |    -> WhiteWizardRedDragonSubHandler     |
                |                                          |
                |  on_notify_text(text):                   |
                |    -> GoldenInvasionSubHandler           |
                |    -> WhiteWizardRedDragonSubHandler     |
                +------------------------------------------+
                               |
                               v
                +------------------------------------------+
                |  Moi sub-handler xu ly doc lap           |
                |  theo logic rieng (xem file rieng)       |
                +------------------------------------------+
```

---

## 3. MO TA HOAT DONG

### 3.1. Luong chinh

**Buoc 1: Khoi tao subscriptions**
- Input: `monster_invasion_enabled = true`, ROI Vung 1 va Vung 2 hop le
- Xu ly:
  - Tao OCRSubscription cho Vung 1 voi callback `on_channel_text`
  - Tao OCRSubscription cho Vung 2 voi callback `on_notify_text`
  - Subscribe ca 2 vao ScreenScanService
  - Khoi tao cac sub-handler dang enabled
- Output: 2 subscriptions active

**Buoc 2: Fan-out OCR text**
- Input: OCR text tu ScreenScanService callback
- Xu ly:
  - `on_channel_text(text)`: goi `sub_handler.on_channel_text(text)` cho moi sub-handler enabled
  - `on_notify_text(text)`: goi `sub_handler.on_notify_text(text)` cho moi sub-handler enabled
  - Moi sub-handler xu ly doc lap, khong anh huong nhau
- Output: Moi sub-handler tu quyet dinh gui Telegram hay khong

**Buoc 3: Teardown**
- Input: Action stop/cancel
- Xu ly: Unsubscribe ca 2 subscriptions, reset tat ca sub-handlers
- Output: Khong con subscription active

### 3.2. Edge Cases

**Case 1: Tat ca sub-events bi tat**
- Xu ly: Khong tao subscription, log canh bao

**Case 2: ROI chua cau hinh**
- Xu ly: Hien thi canh bao, khong subscribe

**Case 3: Them sub-event moi**
- Xu ly: Them sub-handler moi vao MonsterInvasionHandler, dang ky checkbox trong UI. Khong can thay doi subscription logic.

**Case 4: Sub-handler throw exception**
- Xu ly: Catch exception, log loi, tiep tuc fan-out cho sub-handler con lai

### 3.3. Error Handling

**Loi 1: ROI khong hop le**
- Nguyen nhan: Nguoi dung chua chon Teaching image
- Xu ly: Hien thi canh bao trong app, khong bat dau subscription

**Loi 2: Cap nhat UI tu background thread**
- Nguyen nhan: OCR callback chay trong scan thread
- Xu ly: Tat ca cap nhat UI qua Qt signals voi QueuedConnection

---

## 4. PHAC THAO UI

```
+------------------------------------------------------------------+
|  Cai dat Passive Read Action                                  [X] |
+------------------------------------------------------------------+
|  Che do: [Special Event Tracking          v]                     |
+------------------------------------------------------------------+
|  Special Events                                                  |
|                                                                  |
|  [x] Monster Invasion                                            |
|  +----------------------------------------------------------+    |
|  |  -- Vung 1: Channel ------------------------------------ |    |
|  |  Teaching image ROI: (10, 20) -> (200, 50)              |    |
|  |  [Select Channel ROI]                                   |    |
|  |  OCR Engine: [EasyOCR              v]                   |    |
|  |  [Test Algorithms - Channel]                            |    |
|  |  Selected Algorithms: [...]                             |    |
|  |                                                         |    |
|  |  -- Vung 2: Thong bao --------------------------------- |    |
|  |  Teaching image ROI: (10, 100) -> (600, 300)            |    |
|  |  [Select Notify ROI]                                    |    |
|  |  OCR Engine: [EasyOCR              v]                   |    |
|  |  [Test Algorithms - Thong bao]                          |    |
|  |  Selected Algorithms: [...]                             |    |
|  |                                                         |    |
|  |  Match threshold: [70] %                                |    |
|  |                                                         |    |
|  |  -- Sub-events ---------------------------------------- |    |
|  |  [x] Golden Invasion                                    |    |
|  |  +--------------------------------------------------+   |    |
|  |  |  Server time: [ ] 00:40  [x] 01:30              |   |    |
|  |  +--------------------------------------------------+   |    |
|  |                                                         |    |
|  |  [x] White Wizard + Red Dragon                          |    |
|  |  (khong co settings rieng - dung chung ROI/engine)      |    |
|  +----------------------------------------------------------+    |
|                                                                  |
+------------------------------------------------------------------+
|                                              [Luu]  [Huy]       |
+------------------------------------------------------------------+
```

---

## 5. PERSISTENCE RULES

| Buoc | Mo ta                                                        | Truong lien quan                                                                                                                                                                                                                                 |
|------|--------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1    | Them Monster Invasion section vao dialog                     | `monster_invasion_checkbox`, `monster_invasion_widget`                                                                                                                                                                                           |
| 2    | Luu vao action object trong `get_settings()`                 | Tat ca `monster_invasion_*` fields + sub-event fields                                                                                                                                                                                            |
| 3    | Load tu action object trong `_load_settings()`               | Tat ca fields                                                                                                                                                                                                                                    |
| 4    | Them truong vao `_action_to_dict()` trong `tool_manager.py`  | Tat ca fields                                                                                                                                                                                                                                    |
| 5    | Them truong vao `from_dict()` trong `tool_manager.py`        | default: enabled=false, match_threshold=70.0, ocr_engine="auto", algorithms=[], ROI=0, teaching_image_path=""                                                                                                                                    |
| 6    | ROI luu rieng theo vung, khong dung chung voi action         | `monster_invasion_channel_roi_*`, `monster_invasion_notify_roi_*`                                                                                                                                                                                |
| 7    | Test: Luu -> dong app -> mo lai -> kiem tra gia tri con dung  | Tat ca fields phai giu nguyen                                                                                                                                                                                                                    |

> Chi tiet persistence cua tung sub-event xem trong file requirements rieng cua sub-event do.
