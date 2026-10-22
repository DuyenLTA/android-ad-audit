# Audit checklist ads — Nexus AI (`ai.photogenerator.aivideo.aivideogenerator.aiart`)

- **Run:** `wf_4f45973e-19b` · **Chế độ:** capture (máy thật, `pm clear`, log mới)
- **Build:** versionCode **29** · audited_at 2026-10-22T12:56:26Z
- **Capture:** `apk_scan_applicable=true`, `build_ad_ids=86`, `dev_build_signals=0`,
  `missed_home=[new, old]`, `empty_filters=[RemoteConfigRepository, inter_ads, loadInterstitialAd]`
- **Kết quả:** **69/72 khớp · 3 lệch**

| Section | Khớp |
|---|---|
| 1. Thông số kỹ thuật | 8/8 |
| 2. ID ads FO | 40/40 |
| 3. ID ads inapp | 15/18 |
| 4. ID ads resume | 6/6 |

So với lượt trước (vc24, 2026-09-14, run `wf_5185b435-021`: 71/72): `delta.broke` = `reward_img_vid_high`, `reward_img_vid`. `inter_feature_high` lệch từ vc24, vẫn lệch.

## Kết quả fan-out

| Nhóm | Dòng | Kết luận |
|---|---|---|
| confirmed | `inter_feature_high` (Home) | build thiếu tầng high |
| disputed | `reward_img_vid_high` + `reward_img_vid` (Generate Image/Video) | agent: build thiếu → phản biện: checklist cũ, placement đã đổi tên |
| unresolved | — | — |

### confirmed — `inter_feature_high`

- Sheet: `ca-app-pub-4973559944609228/4070123043`. Không có trong `build_ad_ids`; `apk_strings` → `KHÔNG 4070123043`.
- Tên placement vắng: `KHÔNG inter_feature_high`, `KHÔNG feature_high`, `inter_feature_`, `inter_features`, `inter_feature2`.
- Twin normal có: `inter_feature` CÓ (classes.dex), `4098057173` CÓ (classes2.dex) và trong `build_ad_ids` → build chỉ cài tầng normal.
- App ghi tên high dạng literal (`inter_style_high`, `inter_uninstall_high`, `native_*_high`, `result_img_vid_high` đều CÓ) → vắng literal nghĩa là chưa thêm placement, không phải ghép chuỗi lúc chạy.
- Log không góp gì: vùng inter rỗng (`inter_ads`, `loadInterstitialAd` trong `empty_filters`). Kết luận chỉ dựa APK.
- Caveat: 13 ID production ngoài checklist (dưới) — chưa loại hẳn khả năng một trong số đó là high ID gắn tên khác; không chuỗi placement nào gợi ý vậy.

### disputed — `reward_img_vid_high` + `reward_img_vid`

- Sheet: `/8037302182` (high), `/5411138843` (normal). Cả hai vắng `build_ad_ids` và APK; `KHÔNG reward_img_vid`, `reward_img_vid_high`, `rewarded_img`, `reward_generate`.
- Agent kết luận `build-thieu`. Phản biện **làm đổ**: APK có bộ reward đầy đủ dưới tên khác mà checklist không liệt kê — `reward_img_template`, `reward_img_template_high`, `reward_vid_template`, `reward_vid_template_high` đều CÓ (classes.dex).
- Phản biện chỉnh lại bằng chứng agent: chuỗi `_img_vid` / `img_vid_high` trong APK là của `result_img_vid(_high)` (dòng khác, đã khớp, `7459488190`), không phải reward đổi tên.
- Log FA-SVC `ad_unit_id` quanh dòng 2570–4273 thuộc app anh em `com.aivideogenerator.aiphotoeditor...` → không dùng làm bằng chứng.
- Giả thuyết hợp lý nhất: reward Generate Image/Video đã tách thành img/vid template và chuyển sang ID mới → checklist chưa cập nhật. **Cần ads-team/dev xác nhận** mapping.

## 13 ID production trong build, không khớp dòng checklist nào

`ca-app-pub-4973559944609228/` + `1396064413`, `2585857152`, `2709146085`, `2733004612`, `3416557245`, `4469036035`, `4742256365`, `5782117702`, `6587932917`, `7838183830`, `8102082720`, `9082982744`, `9139657213`.

`delta.new_leftover_ids` rỗng vì field này chỉ báo ID *mới* thừa so với snapshot trước — ID thừa sẵn từ trước không được cảnh báo.

## Hạn chế capture

- `missed_home=[new, old]`: cả hai luồng chưa tới Home → im lặng log không dùng làm bằng chứng.
- Vùng log inter + RemoteConfig rỗng → mọi kết luận lượt này dựa APK, không dựa log.

## Lỗ hổng tool

Tool chỉ đối chiếu chiều sheet → build. ID sheet vắng APK thì gắn ngay "không có trong build", không xét build có placement/ID cùng loại không khớp dòng nào. Đề xuất: khi dòng vắng APK mà build có leftover ID hoặc placement cùng loại (`reward_*`, `inter_*`) không khớp dòng nào → gắn "checklist-sai / cần dev map", và in toàn bộ leftover thay vì chỉ ID mới.

## Ghi chú vận hành

Lượt đầu trong phiên hỏng ở bước tải sheet (`requests` treo/400 do IPv6 chập chờn tới `*.googleusercontent.com`). Đã sửa: `checklist_source.sheet_get` ép IPv4; 299 test pass.

## Câu hỏi chưa giải quyết

- 4 placement `reward_*_template*` dùng ID nào trong 13 ID thừa? Checklist có thay `reward_img_vid*` bằng 4 dòng mới không?
- `inter_feature_high` cố ý bỏ ở vc29 hay quên?
