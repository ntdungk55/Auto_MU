# Requirements Document

## Introduction

Thêm OCR Testing section vào Algorithm Testing Dialog để cho phép test và so sánh kết quả OCR từ các engine khác nhau trên ảnh đã được áp dụng thuật toán preprocessing.

## Glossary

- **OCR_Engine**: Công cụ nhận diện chữ (WinRT OCR, Tesseract)
- **Algorithm_Testing_Dialog**: Dialog hiện tại để test thuật toán preprocessing
- **Screenshot_Image**: Ảnh screenshot đang được chọn trong preview (từ Window Captures List)
- **Fixed_ROI**: Vùng cố định được định nghĩa trong READ_PASSIVE action settings
- **Preprocessing_Result**: Ảnh sau khi áp dụng các thuật toán preprocessing
- **OCR_Result**: Kết quả nhận diện chữ bao gồm text, confidence, thời gian xử lý, tên thuật toán, tên screenshot

## Requirements

### Requirement 1: OCR Testing Layout

**User Story:** Là một developer, tôi muốn có layout riêng để test OCR, để tôi có thể so sánh kết quả từ các engine khác nhau.

#### Acceptance Criteria

1. THE Algorithm_Testing_Dialog SHALL giữ nguyên tất cả layout hiện tại
2. THE OCR_Testing_Section SHALL được thêm vào phần Process Algorithm
3. THE OCR_Testing_Section SHALL nằm cạnh bảng thuật toán (horizontal layout)
4. THE OCR_Layout SHALL chứa dropdown để chọn OCR engine hiện có trong app
5. THE OCR_Layout SHALL chứa button "Run OCR" để thực hiện test OCR với engine đã chọn
6. THE OCR_Layout SHALL chứa bảng kết quả hiển thị thông tin OCR
7. THE OCR_Layout SHALL có kích thước phù hợp với không gian trong Process Algorithm section

### Requirement 2: OCR Engine Selection

**User Story:** Là một developer, tôi muốn chọn OCR engine cụ thể để test, để tôi có thể so sánh hiệu quả của từng engine riêng biệt.

#### Acceptance Criteria

1. THE OCR_Testing_Section SHALL hỗ trợ tất cả OCR engines hiện có trong app
2. THE OCR_Testing_Section SHALL tự động detect các OCR engines available (WinRT, Tesseract, Auto)
3. THE OCR_Testing_Section SHALL có dropdown để chọn engine từ danh sách engines hiện có
4. WHEN user click "Run OCR", THE System SHALL chạy OCR engine đã chọn
5. THE System SHALL xử lý trường hợp engine không khả dụng
6. THE System SHALL hiển thị "N/A" nếu engine không available

### Requirement 3: OCR Input Processing

**User Story:** Là một developer, tôi muốn OCR chạy trên ảnh screenshot đang được chọn với vùng ROI (nếu có), để tôi có thể test OCR trên đúng vùng quan tâm.

#### Acceptance Criteria

1. WHEN user click "Run OCR", THE System SHALL lấy ảnh screenshot đang được chọn trong preview
2. IF action có Fixed_ROI (từ READ_PASSIVE action settings), THEN THE System SHALL chỉ đọc trong vùng ROI đó
3. IF action không có Fixed_ROI, THEN THE System SHALL đọc toàn bộ ảnh screenshot
4. THE System SHALL áp dụng tất cả thuật toán preprocessing đã cấu hình lên vùng ảnh được chọn
5. THE System SHALL sử dụng Preprocessing_Result làm input cho OCR engine
6. IF không có ảnh screenshot được chọn, THEN THE System SHALL hiển thị thông báo lỗi

### Requirement 4: OCR Results Display

**User Story:** Là một developer, tôi muốn xem kết quả OCR chi tiết với thông tin về thuật toán và screenshot, để tôi có thể đánh giá chất lượng nhận diện của từng engine với từng cấu hình.

#### Acceptance Criteria

1. THE OCR_Results_Table SHALL hiển thị số thứ tự cho mỗi lần test
2. THE OCR_Results_Table SHALL hiển thị tên OCR engine đã sử dụng
3. THE OCR_Results_Table SHALL hiển thị danh sách tên thuật toán đã áp dụng
4. THE OCR_Results_Table SHALL hiển thị tên ảnh screenshot đã phân tích
5. THE OCR_Results_Table SHALL hiển thị text được nhận diện
6. THE OCR_Results_Table SHALL hiển thị confidence score (nếu có)
7. THE OCR_Results_Table SHALL hiển thị thời gian xử lý (milliseconds)
8. WHEN user click "Run OCR", THE System SHALL thêm 1 dòng mới vào bảng (không thay thế dòng cũ)
9. THE OCR_Results_Table SHALL có khả năng scroll khi có nhiều kết quả

### Requirement 5: OCR Error Handling

**User Story:** Là một developer, tôi muốn hệ thống xử lý lỗi OCR một cách graceful, để tôi có thể tiếp tục test với các engine khác.

#### Acceptance Criteria

1. IF OCR engine không khả dụng, THEN THE System SHALL hiển thị "N/A" trong bảng kết quả
2. IF OCR engine gặp lỗi, THEN THE System SHALL hiển thị thông báo lỗi trong bảng
3. THE System SHALL tiếp tục test với các engine khác khi một engine gặp lỗi
4. THE System SHALL log chi tiết lỗi để debug

### Requirement 6: User Interface Integration

**User Story:** Là một developer, tôi muốn OCR section tích hợp mượt mà với dialog hiện tại, để tôi có thể sử dụng dễ dàng.

#### Acceptance Criteria

1. THE OCR_Layout SHALL không ảnh hưởng đến chức năng hiện tại của dialog
2. THE OCR_Layout SHALL có styling nhất quán với dialog hiện tại
3. THE Dialog SHALL tự động resize để chứa OCR section
4. THE OCR_Section SHALL có thể ẩn/hiện nếu cần thiết

---

## SƠ ĐỒ HOẠT ĐỘNG

```
┌─────────────────┐
│  User click     │
│  "Run OCR"      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Kiểm tra       │
│  screenshot     │
│  được chọn      │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Có ảnh  │
    │ không?  │
    └─┬────┬──┘
      │    │
   YES│    │NO
      │    │
      ▼    ▼
┌─────────────────┐  ┌─────────────────┐
│  Kiểm tra       │  │  Hiển thị       │
│  Fixed ROI      │  │  lỗi "No image" │
└────────┬────────┘  └─────────────────┘
         │
    ┌────┴────┐
    │ Có ROI  │
    │ không?  │
    └─┬────┬──┘
      │    │
   YES│    │NO
      │    │
      ▼    ▼
┌─────────────────┐  ┌─────────────────┐
│  Crop ảnh theo  │  │  Dùng toàn bộ   │
│  Fixed ROI      │  │  ảnh screenshot │
└────────┬────────┘  └────────┬────────┘
         │                    │
         └────────┬───────────┘
                  │
                  ▼
┌─────────────────┐
│  Áp dụng tất cả │
│  thuật toán     │
│  preprocessing  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lấy OCR engine │
│  đã chọn        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Chạy OCR       │
│  + đo thời gian │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Thành   │
    │ công?   │
    └─┬────┬──┘
      │    │
   YES│    │NO
      │    │
      ▼    ▼
┌─────────────────┐  ┌─────────────────┐
│  Lưu kết quả    │  │  Lưu lỗi        │
│  (engine, algo, │  │  vào kết quả    │
│   screenshot,   │  │                 │
│   text, conf,   │  │                 │
│   time)         │  │                 │
└────────┬────────┘  └────────┬────────┘
         │                    │
         └────────┬───────────┘
                  │
                  ▼
┌─────────────────┐
│  Thêm 1 dòng    │
│  mới vào bảng   │
│  kết quả        │
└─────────────────┘
```

---

## MÔ TẢ HOẠT ĐỘNG

### 3.1. Luồng chính

**Bước 1: User click "Run OCR"**
- Input: User action
- Process: Trigger OCR testing process
- Output: Bắt đầu quá trình test OCR

**Bước 2: Kiểm tra screenshot được chọn**
- Input: Current dialog state
- Process: Kiểm tra xem có ảnh screenshot nào đang được chọn trong preview không
- Output: Boolean (có ảnh hay không)

**Bước 3: Kiểm tra Fixed ROI**
- Input: READ_PASSIVE action settings
- Process: Kiểm tra xem action có Fixed_ROI được định nghĩa không
- Output: ROI coordinates hoặc None

**Bước 4: Xác định vùng ảnh cần đọc**
- Input: Screenshot image + Fixed_ROI (nếu có)
- Process: 
  - Nếu có Fixed_ROI: Crop ảnh theo ROI coordinates
  - Nếu không có Fixed_ROI: Dùng toàn bộ ảnh screenshot
- Output: Image region to process

**Bước 5: Áp dụng preprocessing**
- Input: Image region + current algorithm settings
- Process: Áp dụng tất cả thuật toán preprocessing đã cấu hình trong danh sách
- Output: Preprocessed image

**Bước 6: Lấy OCR engine đã chọn**
- Input: OCR engine dropdown selection
- Process: Lấy engine đã được chọn từ dropdown (WinRT, Tesseract, Auto)
- Output: Selected OCR engine

**Bước 7: Chạy OCR**
- Input: Preprocessed image + OCR engine
- Process: Thực hiện OCR + đo thời gian xử lý
- Output: OCR result (text, confidence, processing time) hoặc error

**Bước 8: Thêm kết quả vào bảng**
- Input: OCR result + engine name + algorithm list + screenshot name
- Process: Format và thêm 1 dòng mới vào bảng kết quả (không thay thế dòng cũ)
- Output: Updated results table với dòng mới

### 3.2. Các trường hợp ngoại lệ (Edge Cases)

**Case 1: Không có screenshot được chọn**
- Xử lý: Hiển thị thông báo "Please select a screenshot image first"

**Case 2: OCR engine không khả dụng**
- Xử lý: Hiển thị "N/A" trong cột tương ứng

**Case 3: Fixed ROI nằm ngoài phạm vi ảnh**
- Xử lý: Hiển thị "Invalid ROI coordinates" trong kết quả

**Case 4: Ảnh preprocessing kết quả rỗng**
- Xử lý: Hiển thị "Invalid preprocessed image" trong kết quả

**Case 5: Text nhận diện quá dài**
- Xử lý: Truncate text và thêm "..." ở cuối

**Case 6: Không có thuật toán nào được cấu hình**
- Xử lý: Chạy OCR trên ảnh gốc (không preprocessing), hiển thị "None" trong cột Algorithms

### 3.3. Xử lý lỗi (Error Handling)

**Lỗi 1: OCR engine crash**
- Nguyên nhân: Engine gặp lỗi internal
- Xử lý: Catch exception, hiển thị "Error: [error message]" trong bảng

**Lỗi 2: Preprocessing thất bại**
- Nguyên nhân: Thuật toán preprocessing gây lỗi
- Xử lý: Sử dụng ảnh gốc (hoặc ảnh ROI) cho OCR, log warning

**Lỗi 3: Fixed ROI không hợp lệ**
- Nguyên nhân: ROI coordinates nằm ngoài phạm vi ảnh
- Xử lý: Hiển thị "Invalid ROI", suggest kiểm tra lại ROI settings

---

## PHÁC THẢO UI

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│  Algorithm Testing Dialog                                                        [X]│
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                    Preview Area (Teaching + Window Capture)                     │ │
│  │  ┌─────────────────────────┐  ┌─────────────────────────────────────────────┐  │ │
│  │  │   Teaching Preview      │  │        Window Capture Preview               │  │ │
│  │  │                         │  │        (Screenshot được chọn)               │  │ │
│  │  │                         │  │                                             │  │ │
│  │  └─────────────────────────┘  └─────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                           Window Captures List                                  │ │
│  │  [Capture 1] [Capture 2] [Capture 3] [Load Images] [Capture New]              │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                          Process Algorithm Section                              │ │
│  │  ┌─────────────────────────────┐  ┌─────────────────────────────────────────┐  │ │
│  │  │     Algorithm Management    │  │        OCR Testing Section              │  │ │
│  │  │                             │  │                                         │  │ │
│  │  │  [Algorithm Dropdown] [Add] │  │  Engine: [Auto ▼]  [Run OCR]           │  │ │
│  │  │                             │  │                                         │  │ │
│  │  │  ┌─────────────────────────┐ │  │  ┌─────────────────────────────────────┐ │  │
│  │  │  │   Algorithm List        │ │  │  │        OCR Results Table            │ │  │
│  │  │  │                         │ │  │  ├────┬────────┬──────────┬──────────┬──┤ │  │
│  │  │  │  - Upscale 2x           │ │  │  │No. │Engine  │Algorithms│Screenshot│..│ │  │
│  │  │  │  - Enhance Contrast     │ │  │  ├────┼────────┼──────────┼──────────┼──┤ │  │
│  │  │  │  - Sharpen              │ │  │  │ 1  │WinRT   │Upscale,  │capture1  │..│ │  │
│  │  │  │                         │ │  │  │    │        │Contrast  │          │  │ │  │
│  │  │  └─────────────────────────┘ │  │  │ 2  │Tesser. │Upscale,  │capture1  │..│ │  │
│  │  │                             │  │  │    │        │Sharpen   │          │  │ │  │
│  │  └─────────────────────────────┘  │  │ 3  │WinRT   │None      │capture2  │..│ │  │
│  │                                    │  │... │  ...   │   ...    │   ...    │..│ │  │
│  │                                    │  └─────────────────────────────────────┘ │  │
│  │                                    │  │Text│Conf│Time│                       │  │
│  │                                    │  ├────┼────┼────┤                       │  │
│  │                                    │  │Helo│95% │120 │ (Cột tiếp theo)       │  │
│  │                                    │  │Helo│87% │250 │                       │  │
│  │                                    │  │Hi  │92% │110 │                       │  │
│  │                                    │  │... │... │... │                       │  │
│  │                                    │  └───────────────┘                       │  │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────────┐ │
│  │                            Testing Controls                                     │ │
│  │  [Test Checked Images] [Stop] [Progress Bar]                                   │ │
│  └─────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                     │
│  [Apply to Template Matching]  [Apply to OCR Mode]  [OK]  [Cancel]                │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

**Mô tả các thành phần:**
- **Engine Dropdown**: Chọn OCR engine để test (Auto, WinRT, Tesseract)
- **Run OCR Button**: Chạy OCR test trên ảnh screenshot đang được chọn trong preview
- **OCR Results Table**: Hiển thị kết quả với các cột:
  - No.: Số thứ tự lần test (mỗi lần click "Run OCR" thêm 1 dòng mới)
  - Engine: Tên OCR engine đã sử dụng (WinRT, Tesseract, Auto)
  - Algorithms: Danh sách tên thuật toán đã áp dụng (ví dụ: "Upscale, Contrast, Sharpen" hoặc "None" nếu không có)
  - Screenshot: Tên ảnh screenshot đã phân tích (ví dụ: "capture1.png")
  - Text: Text được nhận diện (truncate nếu quá dài)
  - Conf: Confidence score (% nếu có, N/A nếu không)
  - Time: Thời gian xử lý (milliseconds)
- **Input logic**: 
  - Đọc từ ảnh screenshot đang được chọn (không phải teaching image)
  - Nếu có Fixed ROI → Chỉ đọc vùng ROI
  - Nếu không có Fixed ROI → Đọc toàn bộ ảnh
- **Scroll support**: Bảng có thể scroll khi có nhiều kết quả
- **Layout integration**: OCR section nằm cạnh bảng thuật toán trong phần Process Algorithm