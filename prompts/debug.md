# Template: สั่ง debug (หา root cause ก่อนแก้)

Role: senior developer ที่หา root cause ก่อนแก้
Context: อาการ: <error หรือ behavior ที่ผิด>
  ขั้นตอนทำซ้ำ: <steps>   stack trace / log: <แนบ>
  สภาพแวดล้อม: <version, OS, config>
Task: หา root cause และเสนอวิธีแก้ที่เล็กที่สุด
Constraint: อย่าเพิ่งแก้ จนกว่าจะอธิบายสาเหตุพร้อมหลักฐาน (บรรทัดโค้ด ค่าตัวแปร)
  เขียน test ที่ทำให้ bug เกิดซ้ำได้ก่อน
  ห้ามแก้หรือลบ test เดิม ถ้า test เดิมผิด ให้รายงาน
Format: 1) สมมติฐานเรียงตามความน่าจะเป็น 2) หลักฐาน 3) test ที่ fail
  4) การแก้ 5) ผล test หลังแก้
