## 1. TDD Red：编写 API 层集成测试

- [ ] 1.1 创建 `apps/api/tests/test_url_safety_integration.py`，覆盖 `/api/tasks` 端点拒绝 localhost、内网 IP、回环、非 http 协议、空 URL、纯文本（10 个测试）
- [ ] 1.2 覆盖 `/api/parse` 端点拒绝 localhost、内网 IP、保留地址（3 个测试）
- [ ] 1.3 覆盖 `/api/tasks` 接受公网 URL 正常创建任务（1 个测试）

## 2. TDD Red：补充 unit test 缺口

- [ ] 2.1 在 `test_url_normalization.py` 中补充 multicast IP 拒绝测试
- [ ] 2.2 补充 `*.invalid` TLD 域名拒绝测试
- [ ] 2.3 补充 IPv6 私有地址 (fc00::/7) 拒绝测试
- [ ] 2.4 补充 IPv6 链路本地 (fe80::/10) 拒绝测试
- [ ] 2.5 补充 IPv6 组播地址 (ff00::/8) 拒绝测试

## 3. TDD Green：验证全部测试通过

- [ ] 3.1 运行 `npm test`，确认全部测试通过（预期 175+ tests）

## 4. 提交与推送

- [ ] 4.1 `test:` 提交：API 层集成测试 + unit test 补充
- [ ] 4.2 推送到远程分支

## 5. 创建 PR 并验证

- [ ] 5.1 创建 PR，关联 STE-263，填写 Test-first Evidence
- [ ] 5.2 验证 CI 通过
