'use client';

import { Eye, EyeSlash } from '@phosphor-icons/react';
import { type ComponentProps, useState } from 'react';
import {
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/components/ui/input-group';

export function PasswordInput(props: ComponentProps<typeof InputGroupInput>) {
  const [visible, setVisible] = useState(false);
  return (
    <>
      <InputGroupInput {...props} type={visible ? 'text' : 'password'} />
      <InputGroupAddon align="inline-end">
        <InputGroupButton
          aria-label={visible ? '隐藏密码' : '显示密码'}
          aria-pressed={visible}
          onClick={() => setVisible(!visible)}
          size="icon-sm"
        >
          {visible ? <EyeSlash aria-hidden /> : <Eye aria-hidden />}
        </InputGroupButton>
      </InputGroupAddon>
    </>
  );
}
