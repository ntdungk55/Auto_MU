# Feature: Algorithm Parameters Settings Dialog

## 1. Tổng quan
Cho phép user điều chỉnh parameters của từng thuật toán đã thêm vào preprocessing pipeline bằng cách double-click vào item trong list.

## 2. User Stories
- Là người dùng, tôi muốn double-click vào thuật toán trong pipeline, để mở dialog chỉnh parameters
- Là người dùng, tôi muốn thấy preview ngay khi thay đổi parameters, để biết kết quả trước khi apply
- Là người dùng, tôi muốn click OK để lưu thay đổi, hoặc Cancel để hủy
- Là người dùng, tôi muốn step size phù hợp với giá trị (ví dụ: max=100 thì step=1), để dễ điều chỉnh

## 3. Acceptance Criteria
1. Double-click vào item trong pipeline list → mở Settings dialog
2. Dialog hiển thị tất cả parameters của thuật toán đó
3. Mỗi parameter có widget phù hợp (QSpinBox cho int, QDoubleSpinBox cho float)
4. Step size được tính tự động dựa trên range (max - min)
5. Khi thay đổi parameter → preview ngay lập tức trên ảnh
6. Click OK → lưu parameters vào pipeline và apply thật
7. Click Cancel → restore parameters cũ và revert preview
8. Khi thêm thuật toán mới → dùng default parameters, không mở dialog

## 4. Input/Output

**Input:**
- User double-click vào item trong pipeline list
- Thuật toán và parameters hiện tại của item đó

**Output:**
- Dialog với các parameter widgets
- Preview realtime khi thay đổi
- Parameters được update trong pipeline khi OK

## 5. Sơ đồ khối

```
┌─────────────────────────┐
│ User double-click item  │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Mở AlgorithmParamsDialog│
│ - Load current params   │
│ - Backup old params     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ User thay đổi parameter │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Preview ngay lập tức    │
│ (apply pipeline + show) │
└───────────┬─────────────┘
            │
            ▼
      ┌─────┴─────┐
      │           │
      ▼           ▼
  ┌────────┐  ┌────────┐
  │   OK   │  │ Cancel │
  └────┬───┘  └───┬────┘
       │          │
       ▼          ▼
  ┌────────┐  ┌────────────┐
  │ Save   │  │ Restore    │
  │ params │  │ old params │
  └────────┘  └────────────┘
```

## 6. Technical Notes

### Step Size Calculation
```python
# Tự động tính step size dựa trên range
range_value = max_value - min_value
if range_value <= 10:
    step = 1
elif range_value <= 100:
    step = 1
elif range_value <= 1000:
    step = 10
else:
    step = 100
```

### Data Structure
```python
# Pipeline item
{
    "algorithm": "gaussian_blur",
    "params": {
        "kernel_size": 5
    }
}

# Khi edit, backup old params
old_params = item["params"].copy()

# Khi OK, update
item["params"] = new_params

# Khi Cancel, restore
item["params"] = old_params
```

### Preview Logic
```python
# Khi parameter thay đổi:
1. Update temp params
2. Apply toàn bộ pipeline với temp params
3. Display result trên processed_label
4. Không update pipeline thật (chỉ preview)

# Khi OK:
1. Update pipeline[index]["params"] = temp_params
2. Apply pipeline thật
3. Close dialog

# Khi Cancel:
1. Restore old params
2. Apply pipeline với old params
3. Close dialog
```

### UI Components
- QDialog với OK/Cancel buttons
- Dynamic parameter widgets (QSpinBox, QDoubleSpinBox)
- Layout tương tự như code cũ (trước refactor)

### Ràng buộc
- Dialog chỉ mở khi double-click vào item có parameters
- Thuật toán không có parameters (như "upscale_2x") vẫn có thể double-click nhưng dialog sẽ hiển thị "Không có tham số"
- Preview chỉ update processed image, không ảnh hưởng đến pipeline thật cho đến khi OK
