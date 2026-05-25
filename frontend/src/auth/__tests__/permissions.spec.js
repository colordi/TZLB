import { describe, expect, it } from "vitest";

import {
  canAccessRoute,
  getDefaultRouteForUser,
  USER_ROLES,
} from "../permissions.js";

describe("auth/permissions", () => {
  it("管理员默认进入工单录入，调查员默认进入地图", () => {
    expect(getDefaultRouteForUser({ role: USER_ROLES.ADMIN })).toBe("/workorder");
    expect(getDefaultRouteForUser({ role: USER_ROLES.INVESTIGATOR })).toBe("/map");
  });

  it("调查员不能访问要求管理员角色的路由", () => {
    const route = {
      meta: {
        requiredRoles: [USER_ROLES.ADMIN],
      },
    };

    expect(canAccessRoute({ role: USER_ROLES.INVESTIGATOR }, route)).toBe(false);
    expect(canAccessRoute({ role: USER_ROLES.ADMIN }, route)).toBe(true);
  });
});
