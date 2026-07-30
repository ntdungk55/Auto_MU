# Manual Test Plan: Golden Invasion Event Tracker

---

## Dieu kien tien quyet

- App dang chay voi mot tool co action Passive Read
- Telegram da cau hinh token va chat_id
- Game MU Online dang chay (hoac dung man hinh gia lap)

---

## Test Case 1: Cau hinh UI va Persistence

**Muc dich:** Kiem tra UI hien thi dung va settings duoc luu/load lai chinh xac.

**Cac buoc thuc hien:**
1. Mo dialog cai dat Passive Read Action
2. Chon mode "Special Event Tracking"
3. Tick checkbox "Golden Invasion"
4. Kiem tra section settings xuat hien voi 2 vung rieng biet (Vung 1: Channel, Vung 2: Thong bao)
5. Chon Server time: **01:30**
6. Nhan "Select Channel ROI" -> chon vung man hinh chua ten channel
7. Nhan "Select Notify ROI" -> chon vung man hinh chua thong bao game
8. Chon OCR Engine cho Vung 1: **EasyOCR**
9. Chon OCR Engine cho Vung 2: **EasyOCR**
10. Dat Match threshold: **70%**
11. Nhan **Luu**
12. Dong app hoan toan
13. Mo lai app
14. Mo lai dialog cai dat

**Ket qua mong doi:**
- Checkbox "Golden Invasion" van duoc tick
- Server time van la 01:30
- ROI Vung 1 va Vung 2 hien thi dung toa do da chon
- OCR Engine ca 2 vung van la EasyOCR
- Match threshold van la 70%

---

## Test Case 2: Untick checkbox collapse section

**Muc dich:** Kiem tra untick checkbox an section settings.

**Cac buoc thuc hien:**
1. Mo dialog, chon mode "Special Event Tracking"
2. Tick "Golden Invasion" -> section hien ra
3. Untick "Golden Invasion" -> section an di
4. Nhan Luu
5. Mo lai dialog

**Ket qua mong doi:**
- Checkbox khong duoc tick
- Section settings khong hien thi

---

## Test Case 3: Phat hien boss bi tieu diet - channel khong doi

**Muc dich:** Kiem tra gui Telegram khi boss bi tieu diet va channel khong thay doi.

**Dieu kien:**
- Dang trong gio su kien (sau 01:30 hoac 04:30 hoac 07:30...)
- Channel hien tai: CS1 (khong thay doi tu luc su kien bat dau)

**Cac buoc thuc hien:**
1. Cau hinh Golden Invasion voi ROI Vung 1 tro vao ten channel, Vung 2 tro vao chat thong bao
2. Bat action Passive Read
3. Cho den gio su kien
4. De xuat hien thong bao: Kim Thiet Vuong da bi tieu diet boi PlayerX tai Lorencia

**Ket qua mong doi:**
- Telegram nhan duoc message:
  ```
  Kim Thiet Vuong da bi tieu diet o SV CS1
  SV CS1 hien tai con Kim Xa Vuong, Chien Binh Vang, Nguoi May Vang, Kim Ngu Tinh, Kim Ngu Vuong, Kim Xa Thu
  ```
- Ten nguoi choi (PlayerX) KHONG xuat hien trong message

---

## Test Case 4: Khong gui khi channel thay doi

**Muc dich:** Kiem tra bo qua thong bao khi channel da thay doi.

**Dieu kien:**
- Su kien dang ACTIVE, channel ban dau la CS1
- Nguoi dung chuyen sang CS2 trong luc su kien

**Cac buoc thuc hien:**
1. Bat action, cho su kien ACTIVE (channel CS1)
2. Chuyen channel trong game sang CS2
3. De xuat hien thong bao boss bi tieu diet

**Ket qua mong doi:**
- Telegram KHONG nhan duoc message
- Log app hien thi "Channel changed, skip"

---

## Test Case 5: Khong gui trung lap trong cung chu ky

**Muc dich:** Kiem tra chong trung lap trong 3 tieng.

**Cac buoc thuc hien:**
1. De thong bao Kim Thiet Vuong da bi tieu diet xuat hien 2 lan trong cung chu ky

**Ket qua mong doi:**
- Telegram chi nhan duoc 1 message cho Kim Thiet Vuong

---

## Test Case 6: Danh sach con lai cap nhat dung

**Muc dich:** Kiem tra danh sach boss con lai giam dan theo tung kill.

**Cac buoc thuc hien:**
1. De 3 boss bi tieu diet lan luot: Kim Thiet Vuong -> Kim Xa Vuong -> Chien Binh Vang

**Ket qua mong doi:**
- Message 1: con 6 boss (khong co Kim Thiet Vuong)
- Message 2: con 5 boss (khong co Kim Thiet Vuong, Kim Xa Vuong)
- Message 3: con 4 boss (khong co 3 boss tren)

---

## Test Case 7: Tat ca boss bi tieu diet

**Muc dich:** Kiem tra khi tat ca boss bi tieu diet.

**Cac buoc thuc hien:**
1. De tat ca 7 boss bi tieu diet trong cung chu ky

**Ket qua mong doi:**
- Message cuoi cung: "SV CS1 hien tai con (khong con con nao)"
- Sau do he thong chuyen ve WAITING, cho chu ky tiep theo

---

## Test Case 8: Reset theo chu ky 3 tieng

**Muc dich:** Kiem tra reset tu dong sau 3 tieng.

**Cac buoc thuc hien:**
1. De 2 boss bi tieu diet trong chu ky dau
2. Cho den chu ky tiep theo (3 tieng sau)

**Ket qua mong doi:**
- Chu ky moi bat dau: danh sach boss reset ve du 7 con
- Boss da bi tieu diet o chu ky truoc bi tieu diet lai -> van gui Telegram binh thuong

---

## Test Case 9: ROI chua cau hinh

**Muc dich:** Kiem tra canh bao khi ROI chua duoc chon.

**Cac buoc thuc hien:**
1. Tick "Golden Invasion" nhung khong chon ROI
2. Nhan Luu
3. Bat action

**Ket qua mong doi:**
- App hien thi canh bao "Channel ROI chua cau hinh" hoac "Notify ROI chua cau hinh"
- Khong subscribe, khong crash

---

## Test Case 10: Server time 00:40

**Muc dich:** Kiem tra cau hinh server time 00:40.

**Cac buoc thuc hien:**
1. Cau hinh Golden Invasion voi Server time: **00:40**
2. Nhan Luu, dong app, mo lai

**Ket qua mong doi:**
- Radio button 00:40 duoc chon sau khi load lai
- Su kien bat dau luc 00:40, 03:40, 06:40, ...
