# Audit fanout — aitutor.grammar.languagetutor.learnlanguage

- Run: wf_eb012b0b-288 · mode capture (capture mới 05/11/2026 17:07, không reuse) · version_code 1 · tab sheet gid=425214397
- Kết quả: **53/54 dòng khớp, 1 lệch** · leftover ngoài checklist: chỉ chính App ID của build
- missed_home=[] (tới Home) · empty_filters=[RemoteConfigRepository, inter_ads]

## Confirmed (1)

App ID (1. Thông số kỹ thuật)
- Sheet: `ca-app-pub-4973559944609228~6064663047`
- Build: `ca-app-pub-4973559944609228~1208093315`
- Bằng chứng: chạy apk_strings trên APK thì KHÔNG thấy ~6064663047, nhưng CÓ ~1208093315 trong AndroidManifest.xml. Capture log, tag UserMessagingPlatform/AdsConsentManager, từ chính process app (pid 19051 dòng 670-671; pid 20799 dòng 19244-19245): "Received app ID: ca-app-pub-4973559944609228~1208093315". Trong toàn log không có ~6064663047.
- Phản biện: đứng. Cần ads-team xác nhận ID nào đúng.
- Ngoài phạm vi: UMP báo "no form(s) configured" (cấu hình tài khoản/PO, không chấm Sai).

## Disputed: 0 · Unresolved: 0

## Tool gap
build_ad_ids không bắt App ID trong manifest nhị phân (UTF-16), chỉ có ID mẫu ca-app-pub-0000000000000000~0000000000. Dòng này không bị ảnh hưởng vì đã có phép kiểm manifest riêng. Nhưng dòng App ID nào chỉ được chấm qua build_ad_ids thì có thể bị đổ nhầm sang "không có trong build".

## Câu hỏi chưa giải quyết
- Không có.
