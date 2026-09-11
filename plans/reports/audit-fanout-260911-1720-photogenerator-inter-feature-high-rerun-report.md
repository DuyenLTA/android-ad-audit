# Audit fan-out — ai.photogenerator.aivideo.aivideogenerator.aiart (rerun `--skip`)

Run: `wf_3e37692f-ce4` · 2026-09-11 17:12–17:19 · 2 agents, 0 lỗi · 155k token

Chế độ `--skip`: không lái máy, phán lại trên triage sẵn có. Build `versionCode 24`,
snapshot audit `2026-09-11T08:27:28+00:00`, delta `changed:false`.

## Kết quả

**71/72 dòng khớp** · 1 lệch · **0 disputed**.

| Mục | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 8/8 |
| 2. ID ads FO | 40/40 |
| 3. ID ads inapp | **17/18** |
| 4. ID ads resume | 6/6 |

| Dòng | Verdict | Verify |
|---|---|---|
| `inter_feature_high` (§3, Home) | sheet ≠ build | holds=true |

Kết luận trùng lượt trước (`wf_8f6c22cc-5a6`) — cùng build, cùng triage. Lượt này
tái kiểm độc lập và thêm bằng chứng mới, không lật kết luận.

## Finding: `inter_feature_high`

- Sheet ghi: `ca-app-pub-4973559944609228/4070123043`
- Build thực dùng: `ca-app-pub-4973559944609228/2733004612`

### Bằng chứng lượt này thêm vào

- Quét lại toàn bộ 3502 entry APK `…-24.apk`: `4070123043` = 0 hit, kể cả **UTF-16LE**
  và tìm **zip lồng**. Regex quét toàn APK thấy **77 ad unit ID**, không ID nào có
  đuôi mở đầu `/407`.
- Log L13444 `FOR_TESTER_LOAD_FAILURE: INTERSTITIAL - …/2733004612 - No fill.`
  → **No fill = AdMob nhận ID hợp lệ**, chỉ không có ad trả về. ID sai định dạng
  hoặc không tồn tại báo lỗi khác.
- L1568 `RemoteConfigRepository: key=enable_401_home_a_inter_high, value=true` +
  L12962 `isRemoteAllowed … remoteValue=true` → slot high của Home **bật thật**.
- Loại `lệch hàng khi parse sheet`: `checklist_source.py:53` lấy `alt_values` theo
  từng hàng cột C; 17/18 dòng cùng mục khớp — lệch hàng thì cả mục phải hỏng.
- Loại `chép nhầm ID từ app anh em`: `4070123043` cũng không có trong APK các app
  còn lại trong cache.
- Cả log chỉ có **2 cặp** `key=<high>_<normal>`; cặp control `9894079845_5704057970`
  khớp chính xác `inter_style_high`/`inter_style` ⇒ quy ước đọc key đúng.

### Bằng chứng lượt trước (vẫn đứng)

- L12958/19531 `canRequestAd: key=…/2733004612_…/4098057173`, nửa normal khớp dòng
  sheet `inter_feature` ⇒ nửa high build dùng là `2733004612`
- L13509/19979 `loadDoubleIds: highPriorityAd=NULL for id=…/2733004612` — runtime
  gọi thẳng ID này ở vị trí **high**, không phải suy diễn từ thứ tự
- L13081 `track_ad_request adunitid=…/2733004612 … ga_screen_class=AIP922AIPhotoVideoMakerMainActivity`
- Dex string table sắp tăng dần, lân cận `3910779284 / 4098057173 / 4112509166`
  liên tục — chỗ `4070123043` phải nằm thì trống ⇒ không phải lỗi quét/nén/obfuscate
- `2733004612` nằm trong `leftover_ids` của snapshot

### Dè dặt (verify nêu, không lật kết luận)

1. `apk_source.py:58` chỉ pull `base.apk`, không quét split / dynamic feature. Về
   lý thuyết ID có thể nằm ở split; thực tế loại được vì toàn bộ logic Home và cả
   hai ID của cặp đều nằm trong `classes.dex` của base.
2. Nhãn `checklist-sai` là **quy kết**. APK + log chỉ chứng minh hai bên **lệch
   nhau**, chưa phân biệt "sheet ghi sai ID" vs "dev wire nhầm ID".

**Phát biểu nên dùng:** "ID trong sheet không tồn tại trong build; build đang dùng
`2733004612` cho inter high màn Home. Cần ads-team xác nhận ID đúng."

## Thay đổi kèm theo

- `artifact_report_template.html`: cập nhật run id `wf_3e37692f-ce4`, thêm dòng
  `mode: --skip`, trỏ footer sang report này. Metadata mỗi lượt đang **hard-code
  trong template** — mỗi lần chạy phải sửa tay.
- Fragment `-findings.html` / `-notes.html`: thêm dòng log No fill, hai giả thuyết
  mới bị loại (parse lệch hàng, chép nhầm app anh em), caveat split-APK.
- Artifact: https://claude.ai/code/artifact/bd4b9714-a489-4dfa-80b0-a1c6fe1b721b (v4)

## Unresolved

- `4070123043` có tồn tại trong AdMob account `4973559944609228` không, gắn
  placement nào — chỉ tra được qua AdMob console.
- Bên nào sai: sheet hay build — cần ads-team xác nhận.
- Run metadata (run id, số agent, đường dẫn report) hard-code trong
  `artifact_report_template.html`; nên nhận qua CLI flag để builder không phải sửa
  tay mỗi lượt. Chưa làm — ngoài scope lượt chạy này.
