# หา Library ตัดคลิปสไตล์ CapCut + โพสต์ IG/Facebook — สรุปผลค้นคว้า

เอกสารนี้ตอบ 2 คำถามแยกกัน อย่าปนกัน:
1. **ตัดต่อ** — จะใช้อะไรทำคลิปให้ได้ฟีล CapCut (เอฟเฟกต์ ทรานซิชัน แคปชันเด้ง)
2. **โพสต์** — จะใช้อะไรส่งคลิปขึ้น IG/Facebook แบบอัตโนมัติ (ไม่ใช่กดมือ)

ทั้งสองเรื่องเป็นคนละงานกัน คนละ library กัน — "เจอ library ตัดต่อ" ไม่ได้แปลว่าโพสต์ได้ด้วย
และ "เจอ library โพสต์ได้" ไม่ได้แปลว่าตัดต่อสวยขึ้น ต้องเลือกคนละตัวแล้วเอามาต่อกัน

---

## 1) ตัดต่อสไตล์ CapCut

| ตัวเลือก | คืออะไร | ข้อดี | ข้อจำกัด |
|---|---|---|---|
| **ffmpeg (ที่ใช้อยู่ในสกิล `story-editor` ตอนนี้)** | เครื่องมือประมวลผลวิดีโอระดับล่างสุด | เร็วที่สุด ฟรี ควบคุมได้ทุกพิกเซล ที่ทำอยู่ตอนนี้ (BPM sync, ตัวหนังสือไทย, speed ramp) มีคุณภาพเทียบเท่าหรือดีกว่า CapCut อยู่แล้ว | เขียนเอง ต้องคุมทุกอย่างเอง (ที่ผ่านมาเจอบั๊กพวกนี้ตลอด) |
| **MoviePy** (Python) | ห่อ ffmpeg ให้เขียนง่ายขึ้น | อ่านง่ายกว่า ffmpeg ตรงๆ | ช้า ใช้ CPU อย่างเดียว ไม่เหมาะกับงานจำนวนมาก/เรียลไทม์ — **ไม่ได้ดีกว่าที่ทำอยู่** |
| **Remotion** (React/Node) | เขียนวิดีโอด้วยโค้ด React แล้วเรนเดอร์ผ่าน Chromium | เอฟเฟกต์/แอนิเมชันตัวหนังสือทำง่ายมาก (คือ CSS/React) เหมาะกับงานที่มีเทมเพลตซ้ำๆ | ต้องรู้ React เรนเดอร์หนักกว่า ffmpeg (ผ่าน browser) ไม่เหมาะกับ Thai text แบบ raqm ที่ใช้อยู่ |
| **Shotstack / Creatomate / JSON2Video** (Cloud API) | ส่ง JSON template ไป เขาเรนเดอร์ให้แล้วส่ง mp4 กลับ | ไม่ต้องเซตอัพ มีเทมเพลตทรานซิชัน/แคปชันสำเร็จรูปใกล้เคียง CapCut | เสียเงินตามการเรนเดอร์ ข้อความไทยอาจไม่ได้คุมฟอนต์/สระเป๊ะเท่า PIL+raqm ที่ทำเอง |
| **CapCut / Descript / Reap / SendShort** (แอป/SaaS ไม่ใช่ library) | เครื่องมือสำเร็จรูป ตัดต่ออัตโนมัติ (auto-cut, auto-caption) | เร็วสุดถ้าไม่อยากเขียนโค้ดเลย | ควบคุมรายละเอียดไม่ได้เท่าที่ทำเอง ส่วนใหญ่ไม่มี API เปิดให้เขียนสคริปต์ |

**สรุปตรงนี้:** สิ่งที่ `story-editor` ทำอยู่ตอนนี้ด้วย ffmpeg **คือของที่ MoviePy/Remotion ทำแทนไม่ได้ดีกว่า** — ปัญหาที่เจอมาตลอด (บั๊ก typewriter, กลิตช์ไม่ลงจังหวะ) เป็นบั๊กในโค้ดที่เขียน ไม่ใช่ข้อจำกัดของ ffmpeg เอง เปลี่ยนเครื่องมือไม่ได้แก้ปัญหานี้
ถ้าอยากได้ "เทมเพลตสำเร็จรูปกดปุ๊บได้เลย" โดยยอมเสียเงิน ตัวที่น่าลองคือ **Creatomate** (มี template editor + API)

---

## 2) โพสต์ขึ้น Instagram / Facebook อัตโนมัติ

### ทางการ (ของ Meta เอง) — ฟรี แต่ต้องตั้งค่า

| แพลตฟอร์ม | โพสต์อะไรได้ผ่าน API | โพสต์อะไรไม่ได้ |
|---|---|---|
| **Instagram** (Content Publishing API) | Feed (รูป/วิดีโอ/carousel), **Reels** | **Story ยังโพสต์ผ่าน API ไม่ได้** (Meta ยังไม่เปิด endpoint นี้ให้แอปทั่วไป) |
| **Facebook Page** (Video API) | Feed video, **Reels**, และ **Story วิดีโอ** ผ่าน endpoint `/page_id/video_stories` (เพิ่งมี) | — |

ข้อมูลใหม่ที่ต่างจากที่เข้าใจไว้ในสกิล: **FB Story โพสต์ผ่าน API ได้แล้วจริงๆ** (คนละเรื่องกับ IG Story ที่ยังทำไม่ได้)
ของเดิมใน `references/publish.md` เขียนว่า "โพสต์อัตโนมัติไม่ได้" แบบเหมารวมทั้งสองแพลตฟอร์ม — อันนี้ไม่ตรงกับ FB แล้ว ถ้าต้องการให้ผมอัปเดตสกิลตรงนี้บอกได้

**สิ่งที่ต้องมีก่อนใช้ Meta API เอง (ฟรี ไม่ต้องรอ App Review ถ้าโพสต์บัญชีตัวเอง):**
1. เพจ Facebook + บัญชี Instagram ต้องเป็น **Professional (Business/Creator)** และเชื่อมกับเพจ FB
2. สร้าง Meta Developer App (ใส่ตัวเองเป็น Admin/Tester ก็พอ — ไม่ต้องผ่าน App Review เพราะโพสต์บัญชีตัวเอง)
3. ขอ Access Token ที่มีสิทธิ์ `instagram_content_publish` / `pages_manage_posts`
4. เขียนสคริปต์ยิง POST ตามขั้นตอน: สร้าง container → poll สถานะ → publish

ข้อจำกัดจริงจาก Meta: โพสต์ได้สูงสุด **25 โพสต์/วัน ต่อบัญชี IG** (Reels+Story นับรวมกัน)

### ทางอ้อม — Unified API (จ่ายเงิน/self-host แลกกับความง่าย)

| ตัวเลือก | รูปแบบ | ราคา | เหมาะกับ |
|---|---|---|---|
| **[Ayrshare](https://www.ayrshare.com/)** ([Python SDK](https://github.com/ayrshare/social-post-api-python)) | SaaS มี REST/Python/Node SDK ครบ | เริ่ม $149/เดือน | ทีม/โปรดักต์ที่ต้องการความนิ่งสูง ไม่อยากยุ่งกับ OAuth เอง — **แพงเกินไปสำหรับใช้คนเดียว** |
| **[Postiz](https://github.com/gitroomhq/postiz-app)** | โอเพนซอร์ส self-host ฟรี | ฟรี (ต้องมีเซิร์ฟเวอร์รันเอง) | ถ้าไม่อยากยุ่งกับ Graph API เองแต่ก็ไม่อยากจ่ายรายเดือน |

**คำเตือน:** อย่าใช้ library แบบ "ปลอมเป็นแอปมือถือ" (unofficial IG private-API bot) เพื่อโพสต์อัตโนมัติ — ผิด Terms of Service ของ Meta เสี่ยงบัญชีโดนแบน ไม่แนะนำแม้จะมีให้ใช้งานจริงในตลาด

---

## สรุปเชิงแนะนำ (สำหรับงานคนเดียว โพสต์คลิปตัวเอง)

1. **ตัดต่อ** — ใช้ ffmpeg + สกิล `story-editor` เดิมต่อไป ไม่ต้องเปลี่ยน library เอฟเฟกต์ที่มีตอนนี้ทำได้เทียบเท่า CapCut แล้ว ปัญหาที่เจอคือบั๊กโค้ด ไม่ใช่ข้อจำกัดเครื่องมือ
2. **โพสต์** — เริ่มจาก Meta Graph API ตรงๆ (ฟรี ไม่ต้องรอ App Review เพราะโพสต์บัญชีตัวเอง) ได้แค่ FB Feed/Reels/Story + IG Feed/Reels (**IG Story ยังต้องกดมือ**)
   ถ้าตั้งค่า Meta App เองแล้วรู้สึกยุ่งยากเกินไป ค่อยพิจารณา Postiz (ฟรีแต่ต้อง host เอง) ก่อน Ayrshare (จ่ายรายเดือน)

## Sources
- [Publish Content using the Instagram Platform — Meta Developer Docs](https://developers.facebook.com/docs/instagram-platform/content-publishing/)
- [Instagram Reels API: Complete Developer Guide (2026) — Phyllo](https://www.getphyllo.com/post/a-complete-guide-to-the-instagram-reels-api)
- [Stories — Video API — Meta for Developers](https://developers.facebook.com/docs/page-stories-api/)
- [Publish a Reel — Video API — Meta for Developers](https://developers.facebook.com/docs/video-api/guides/reels-publishing/)
- [Graph API Reference v25.0: Page Video Reels](https://developers.facebook.com/docs/graph-api/reference/page/video_reels/)
- [ayrshare/social-post-api-python — GitHub](https://github.com/ayrshare/social-post-api-python)
- [Ayrshare — Unified Social Media API](https://www.ayrshare.com/)
- [Best Social Media APIs For Multi-Platform Posting In 2026 — SocialChamp](https://www.socialchamp.com/blog/best-social-media-apis/)
- [Zulko/moviepy — GitHub](https://github.com/zulko/moviepy)
- [Video as Code: Which Library Should You Choose? — Medium](https://sumeetkg.medium.com/video-as-code-which-library-should-you-choose-8807ac1bda6b)
- [FFmpeg Alternative — Shotstack](https://shotstack.io/solutions/ffmpeg-alternative/)
