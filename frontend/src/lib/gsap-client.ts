'use client';

import { useGSAP } from '@gsap/react';
import gsap from 'gsap';

// Register the React integration once. Component animations still run only
// from useGSAP callbacks after their client DOM has been mounted.
gsap.registerPlugin(useGSAP);

export { gsap, useGSAP };
