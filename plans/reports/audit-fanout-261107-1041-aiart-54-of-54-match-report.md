# Audit fanout — com.ai.art.aiimagegenerator.aivideogenerator.aiphoto.aiart (versionCode 9)

- Run: wf_81c5d773-e07 · mode capture --force · gid 2074057990 (từ sheet, chưa có trong registry)
- Kết quả: 54/54 khớp, chưa kết luận 0 → clean. confirmed 0 / disputed 0 / unresolved 0.
- Lượt đầu của app → delta ghi 54 dòng "mới thêm", không có dòng broke/fixed.
- Capture:
  - new (pm clear): Splash → splash inter → Language 1.1 → Language 2.1 → Onboarding → Question → inter → Main. Tới Home.
  - old (mở lại, giữ data): Splash → VslNativeSplashFullScrActivity, driver hết cách thử, KHÔNG tới Home. Dòng ad luồng old (spl_o, resume…) chỉ được chấm theo phần log đã thu.
- 18 ID trong build không có trên sheet (tool chỉ đối chiếu sheet → build, không coi là lệch); delta đánh dấu 4 ID mới:
  - ca-app-pub-4584260126367940/2455337868
  - ca-app-pub-4584260126367940/7567299405
  - ca-app-pub-4584260126367940/7639810380
  - ca-app-pub-4584260126367940/8385557059
- 5 dòng khớp chỉ nhờ APK (log chưa thấy load): show_305_onb5_n_native, show_301_onb1_o_native_high/native/inter_high/inter — chưa chứng minh placement đang bật.
- Không commit.

## Unresolved questions
- 4 ID ngoài checklist: ads-team xác nhận là ID dự phòng / ID cũ hay cần bổ sung vào sheet.
- Luồng old dừng ở native splash full screen: cần bổ sung bước đóng màn này trong driver nếu muốn chấm đủ luồng old.
