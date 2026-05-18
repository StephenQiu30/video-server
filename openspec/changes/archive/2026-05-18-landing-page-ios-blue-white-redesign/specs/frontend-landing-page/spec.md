## MODIFIED Requirements

### Requirement: Premium Landing Page
The web application SHALL provide a responsive, conversion-oriented, iOS-style SaaS landing page at `/` with a blue-white visual system, clear visual hierarchy, and minimal decorative noise.

#### Scenario: Guest user can理解完整落地页结构
- **WHEN** a guest user访问首页 `/`
- **THEN** the landing page SHALL show the section anchors `hero`、`features`、`proof`、`pricing`、`faq` and `final-cta` in order.
- **AND** each section SHALL contain用户可读的核心文案与至少一个明确转化动作。

#### Scenario: First-time visitor sees可用首屏引导
- **WHEN** 页面进入首屏后首次加载完成
- **THEN** the hero section SHALL render one primary CTA and one secondary CTA with visible focus-visible states.
- **AND** the design SHALL避免夸张渐变和复杂装饰，优先展示简明信息层级。

#### Scenario: 蓝白风格和 iOS 交互一致性
- **WHEN** user interacts with header、buttons、cards
- **THEN** components SHALL保持一致的蓝白配色与圆角比例。
- **AND** touch-target SHALL include `min-h-[44px]`/`min-w-[44px]` where interactive controls are primary。

#### Scenario: 无障碍与降噪
- **WHEN** keyboard、screen reader 或 reduced-motion 用户使用页面
- **THEN**关键交互 SHALL提供 aria-label、focus-visible and honor `prefers-reduced-motion` preferences.
- **AND** 页面 SHALL provide FAQ 的语义化展开逻辑供用户理解使用边界。
