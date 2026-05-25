export const USER_ROLES = Object.freeze({
  ADMIN: "admin",
  INVESTIGATOR: "investigator",
});

const DEFAULT_ROUTE_BY_ROLE = Object.freeze({
  [USER_ROLES.ADMIN]: "/workorder",
  [USER_ROLES.INVESTIGATOR]: "/map",
});

export function getUserRole(user) {
  return typeof user?.role === "string" ? user.role.trim() : "";
}

export function userHasAnyRole(user, requiredRoles = []) {
  if (!Array.isArray(requiredRoles) || requiredRoles.length === 0) {
    return true;
  }
  return requiredRoles.includes(getUserRole(user));
}

export function canAccessRoute(user, route) {
  return userHasAnyRole(user, route?.meta?.requiredRoles);
}

export function getDefaultRouteForUser(user) {
  return DEFAULT_ROUTE_BY_ROLE[getUserRole(user)] || "/map";
}
