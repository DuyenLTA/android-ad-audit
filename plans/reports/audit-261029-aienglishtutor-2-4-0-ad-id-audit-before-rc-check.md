# Audit ID ads · com.nxl.aienglishtutor.ailearnlanguage.aichatbot 2.4.0 (vc22)

- Lượt: trước `/rc-check --next-gen` (bot Discord), máy Pixel 6 `18311FDF60085N`, 29/10/2026
- Chế độ: capture (đã `pm clear` app), workflow run `wf_2e75b0d8-dd4`
- Sheet: tab gid=1899009360 (chưa có trong registry `apps.json`)

## Kết quả

- 54/54 dòng khớp, không đổi so với lần trước, chưa kết luận: 0
- confirmed: 0 · disputed: 0 · unresolved: 0 → **clean**

## Ghi chú

- Capture chưa tới Home ở cả lượt user mới và user cũ: dừng ở `RevenueCatPaywallActivity` (tool không tìm được cách đóng paywall). ID vị trí sau paywall (Home, in-app) không được đối chiếu bằng log ở lượt này.
- Tool chỉ đối chiếu chiều sheet → build.

## Câu hỏi chưa giải quyết

- Cách đóng paywall RevenueCat của app này để capture tới Home.
