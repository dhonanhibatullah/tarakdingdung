export type PermissionName = string;

export function hasPermission(
  permissions: ReadonlySet<string>,
  permission: string,
): boolean {
  return permissions.has(permission);
}

export function canAccessAny(
  permissions: ReadonlySet<string>,
  required: readonly string[],
): boolean {
  return required.length === 0 || required.some((item) => permissions.has(item));
}
