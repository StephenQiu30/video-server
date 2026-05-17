## 1. Core Implementation

- [x] 1.1 Implement URL extraction regex utility inside `apps/api/app/utils/url.py` for maximum centralization. <!-- id: 1 -->
- [x] 1.2 Integrate input sanitization directly in `normalize_user_url` to automatically clean raw sharing links before syntax validation. <!-- id: 2 -->
- [x] 1.3 Correct the nested docker-compose path references (`infra/docker/docker-compose.yml`) in `scripts/start.sh` to use the root `docker-compose.yml`. <!-- id: 3 -->

## 2. Verification & Review

- [x] 2.1 Perform systematic code review of the changes to guarantee simplicity, correctness, and adherence to the MVP pattern. <!-- id: 4 -->
- [x] 2.2 Run native verification with raw Bilibili/Douyin/Kuaishou share text blocks to ensure exact URL extraction. <!-- id: 5 -->
- [x] 2.3 Test `npm run start` and `npm run stop` to confirm that the updated Docker Compose path loads without errors. <!-- id: 6 -->
