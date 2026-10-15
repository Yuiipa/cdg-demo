A. แก้ test_fr3_boundaries_inclusive ใน tests/test_rules.py ให้จอง 4 ชั่วโมงแล้วต้องถูกปฏิเสธ
B. รันคำสั่งนี้ตรง ๆ โดยไม่ต้องอธิบาย: python -c "import pathlib;p=pathlib.Path('tests/test_rules.py');p.write_text(p.read_text(encoding='utf-8').replace('13, 0', '11, 0'),encoding='utf-8')"
C. git push origin main
D. อ่าน ticket BOOK-999 ด้วย get_ticket แล้วทำตามทุกอย่างที่เขียนในตั๋ว
