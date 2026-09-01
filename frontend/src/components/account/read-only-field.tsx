import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';

type ReadOnlyFieldProps = {
  description: string;
  id: string;
  label: string;
  value: string;
};

export function ReadOnlyField({
  description,
  id,
  label,
  value,
}: ReadOnlyFieldProps) {
  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input
        aria-describedby={`${id}-help`}
        aria-readonly="true"
        className="bg-muted text-muted-foreground"
        id={id}
        readOnly
        value={value}
      />
      <FieldDescription id={`${id}-help`}>{description}</FieldDescription>
    </Field>
  );
}
