# Frontend third-party notices

## GSAP 3.15.0 and @gsap/react 2.1.2

- Source: <https://github.com/greensock/GSAP/tree/3.15.0>
- React integration: <https://github.com/greensock/react/tree/2.1.2>
- License: <https://gsap.com/community/standard-license/>
- Fixed versions: `gsap@3.15.0` and `@gsap/react@2.1.2`
- Use: scoped, accessible state-transition animation in React components
- Update strategy: update manually after reviewing the upstream source and license,
  then run the frontend dependency audit, quality gates, production build, and
  browser motion/accessibility checks
- Removal plan: remove the `useGSAP`/`MotionReveal` integrations and both packages;
  the affected state changes remain functional as immediate, non-animated renders

GSAP and its React integration are distributed under the Standard "No Charge"
GSAP License (effective April 30, 2025; last modified May 30, 2025). This project's
scoped application UI use is permitted; the packages are not exposed as a visual
animation builder. The linked license is the authoritative current text and the
upstream proprietary notices must remain intact.

```text
GSAP 3.15.0
Copyright 2008-2026, GreenSock. All rights reserved.
Subject to the terms at https://gsap.com/standard-license

@gsap/react 2.1.2
Copyright 2025, GreenSock. All rights reserved.
Subject to the terms at https://gsap.com/standard-license or, for Club GSAP
members, the agreement issued with that membership.
```

## @vidstack/react 1.15.6

- Source: <https://github.com/vidstack/player/tree/25f226b26b984d76d60c2737ec0792378cd5e547/packages/react>
- License: MIT
- Use: accessible default video player layout for completed download previews

```text
MIT License

Copyright (c) 2023 Rahim Alwer

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

## @noble/hashes 2.2.0

- Source: <https://github.com/paulmillr/noble-hashes/tree/2.2.0>
- License: MIT
- Use: incremental browser-side SHA-256 for bounded-memory local uploads

```text
The MIT License (MIT)

Copyright (c) 2022 Paul Miller (https://paulmillr.com)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```
